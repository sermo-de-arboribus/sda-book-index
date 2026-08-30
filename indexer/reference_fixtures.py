from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_INDEX_ENTRY_LABEL_LENGTH = 500


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _reference_fixture_rows(
    payload: dict[str, Any],
    *,
    manifestation_id: int | None,
) -> tuple[list[dict[str, Any]], dict[tuple[int, int], int]]:
    """Build page-reference fixture rows and map parsed positions to Reference PKs."""
    rows: list[dict[str, Any]] = []
    reference_pks: dict[tuple[int, int], int] = {}
    documents = payload.get('documents', {}) or {}
    entries = payload.get('entries', []) or []

    for entry_index, entry in enumerate(entries, start=1):
        references = entry.get('references', []) or []
        for ref_index, reference in enumerate(references, start=1):
            if reference.get('kind') != 'page':
                continue

            document_label = ''
            document_part_of_label = ''
            document_key = reference.get('document')
            if document_key is not None:
                document = documents.get(str(document_key)) or documents.get(document_key)
                if isinstance(document, dict):
                    document_label = document.get('label', '')
                    if document.get('part_of'):
                        parent_document = documents.get(str(document['part_of'])) or documents.get(document['part_of'])
                        if isinstance(parent_document, dict):
                            document_part_of_label = parent_document.get('label', '')

            locator_payloads = _as_list(reference.get('page_locators'))
            raw_reference = '; '.join(
                locator.get('raw', '') for locator in locator_payloads if locator.get('raw')
            ) or entry.get('raw_lemma', '')

            safe_document_label = (document_label or entry.get('raw_lemma', ''))[:1000]
            safe_document_part_of = (document_part_of_label or '')[:1000]

            reference_pk = entry_index * 100 + ref_index
            fields = {
                'manifestation': manifestation_id,
                'raw_document': safe_document_label,
                'raw_document_part_of': safe_document_part_of,
                'source_file': entry.get('source_file', ''),
                'source_paragraph_number': entry.get('paragraph_number'),
                'page_start': 1,
                'page_end': 1,
            }
            if raw_reference and len(raw_reference) <= 1000:
                fields['raw_reference'] = raw_reference

            if locator_payloads:
                first_locator = locator_payloads[0]
                fields['page_start'] = first_locator.get('page_start') or 1
                fields['page_end'] = first_locator.get('page_end') or first_locator.get('page_start') or 1
                fields['page_start_relation'] = first_locator.get('page_start_relation', '')
                fields['page_end_relation'] = first_locator.get('page_end_relation', '')

            rows.append({
                'model': 'indexer.reference',
                'pk': reference_pk,
                'fields': fields,
            })
            reference_pks[(entry_index, ref_index)] = reference_pk

            for locator_index, locator in enumerate(locator_payloads, start=1):
                locator_fields = {
                    'reference': reference_pk,
                    'order': locator_index,
                    'locator_unit': locator.get('locator_unit', ''),
                    'locator_start': locator.get('page_start'),
                    'locator_end': locator.get('page_end'),
                    'start_relation': locator.get('page_start_relation', ''),
                    'end_relation': locator.get('page_end_relation', ''),
                    'locator_scope': locator.get('page_scope', ''),
                    'raw_locator': locator.get('raw', ''),
                    'reference_type_codes': ''.join(sorted(locator.get('reference_types', []))) or '',
                }
                rows.append({
                    'model': 'indexer.referencelocator',
                    'pk': reference_pk * 10 + locator_index,
                    'fields': locator_fields,
                })

    return rows, reference_pks


def build_reference_fixture_rows(payload: dict[str, Any], *, manifestation_id: int | None = None) -> list[dict[str, Any]]:
    """Build Django fixture rows for page-based Reference and ReferenceLocator objects."""
    rows, _ = _reference_fixture_rows(payload, manifestation_id=manifestation_id)
    return rows


def _entry_levels(entry: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    index_type = entry.get('index_type')
    if index_type not in {'P', 'S'}:
        raise ValueError(f"Index entry has unsupported index_type {index_type!r}.")

    levels = entry.get('levels', []) or []
    if not 1 <= len(levels) <= 3:
        raise ValueError('Index entries must contain between one and three levels.')

    labels = tuple(level.get('label', '').strip() for level in levels if isinstance(level, dict))
    if len(labels) != len(levels) or any(not label for label in labels):
        raise ValueError('Index entry levels must have non-empty labels.')
    return index_type, labels


def _level_items(
    levels: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> tuple[tuple[str, tuple[str, ...], str], ...]:
    items: list[tuple[str, tuple[str, ...], str]] = []
    for level in levels:
        if not isinstance(level, dict):
            raise ValueError('Index entry levels must be objects.')
        label = level.get('label', '').strip()
        if not label:
            raise ValueError('Index entry levels must have non-empty labels.')
        metadata_items = level.get('metadata', []) or []
        metadata = tuple(str(item).strip() for item in metadata_items if str(item).strip())
        sort_key = str(level.get('sort_key', '')).strip()
        items.append((label, metadata, sort_key))
    return tuple(items)


def _fixture_levels(
    index_type: str,
    level_items: tuple[tuple[str, tuple[str, ...], str], ...],
) -> tuple[tuple[str, str, tuple[Any, ...]], ...]:
    if index_type != 'P':
        return tuple((label, sort_key, ('single', metadata)) for label, metadata, sort_key in level_items)

    if len(level_items) == 1:
        label, metadata, sort_key = level_items[0]
        return ((label, sort_key, ('single', metadata)),)

    first_label, first_metadata, first_sort_key = level_items[0]
    second_label, second_metadata, second_sort_key = level_items[1]
    person_label = f'{first_label}, {second_label}'
    person_sort_key = f'{first_sort_key}, {second_sort_key}' if first_sort_key and second_sort_key else ''
    fixture_items: list[tuple[str, str, tuple[Any, ...]]] = [
        (person_label, person_sort_key, ('person', first_label, first_metadata, second_label, second_metadata))
    ]
    fixture_items.extend(
        (label, sort_key, ('single', metadata))
        for label, metadata, sort_key in level_items[2:]
    )
    return tuple(fixture_items)


def _truncate_index_entry_label(label: str) -> str:
    return label[:MAX_INDEX_ENTRY_LABEL_LENGTH]


def build_index_fixture_rows(payload: dict[str, Any], *, manifestation_id: int | None = None) -> list[dict[str, Any]]:
    """Build a complete index fixture from parsed ODT output.

    Nodes are shared by index type and complete label path. Parser metadata intentionally remains
    in the source JSON because IndexEntryLabel has no dedicated metadata field.
    """
    entries = payload.get('entries', []) or []
    index_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    entry_reference_rows: list[dict[str, Any]] = []
    cross_reference_rows: list[dict[str, Any]] = []
    node_pks: dict[tuple[str, tuple[tuple[str, tuple[Any, ...]], ...]], int] = {}
    entry_leaf_pks: dict[int, tuple[str, int]] = {}
    next_index_entry_pk = 1
    fixture_timestamp = datetime.now(timezone.utc).isoformat()

    for entry_index, entry in enumerate(entries, start=1):
        index_type, labels = _entry_levels(entry)
        level_items = _level_items(entry.get('levels', []) or [])
        fixture_levels = _fixture_levels(index_type, level_items)
        parent_pk: int | None = None
        for depth, (label, sort_key, metadata_identity) in enumerate(fixture_levels, start=1):
            path = fixture_levels[:depth]
            key = (
                index_type,
                tuple((item_label, item_identity) for item_label, _, item_identity in path),
            )
            node_pk = node_pks.get(key)
            if node_pk is None:
                node_pk = next_index_entry_pk
                next_index_entry_pk += 1
                node_pks[key] = node_pk
                index_rows.append({
                    'model': 'indexer.indexentry',
                    'pk': node_pk,
                    'fields': {
                        'index_type': index_type,
                        'parent': parent_pk,
                        'created_at': fixture_timestamp,
                        'updated_at': fixture_timestamp,
                    },
                })
                label_rows.append({
                    'model': 'indexer.indexentrylabel',
                    'pk': node_pk,
                    'fields': {
                        'index_entry': node_pk,
                        'language': 'de',
                        'label': _truncate_index_entry_label(label),
                        'sort_key': _truncate_index_entry_label(sort_key),
                    },
                })
            parent_pk = node_pk
        entry_leaf_pks[entry_index] = (index_type, parent_pk)

    reference_rows, reference_pks = _reference_fixture_rows(
        payload,
        manifestation_id=manifestation_id,
    )

    next_entry_reference_pk = 1
    next_cross_reference_pk = 1
    for entry_index, entry in enumerate(entries, start=1):
        index_type, source_entry_pk = entry_leaf_pks[entry_index]
        page_order = 0
        cross_reference_order = 0
        for ref_index, reference in enumerate(entry.get('references', []) or [], start=1):
            if reference.get('kind') == 'page':
                page_order += 1
                entry_reference_rows.append({
                    'model': 'indexer.indexentryreference',
                    'pk': next_entry_reference_pk,
                    'fields': {
                        'index_entry': source_entry_pk,
                        'reference': reference_pks[(entry_index, ref_index)],
                        'order': page_order,
                    },
                })
                next_entry_reference_pk += 1
                continue

            if reference.get('kind') not in {'see', 'see_also', 'compare'}:
                continue

            cross_reference_order += 1
            target_levels = reference.get('target_levels', []) or []
            target_items = _level_items(target_levels) if target_levels else ()
            target_path = _fixture_levels(index_type, target_items) if target_items else ()
            target_entry_pk = (
                node_pks.get(
                    (index_type, tuple((item_label, item_identity) for item_label, _, item_identity in target_path))
                )
                if target_path else None
            )
            cross_reference_rows.append({
                'model': 'indexer.indexentrycrossreference',
                'pk': next_cross_reference_pk,
                'fields': {
                    'source_entry': source_entry_pk,
                    'target_entry': target_entry_pk,
                    'kind': reference['kind'],
                    'marker': reference.get('marker', ''),
                    'target_raw': reference.get('target_raw', ''),
                    'order': cross_reference_order,
                },
            })
            next_cross_reference_pk += 1

    return index_rows + label_rows + reference_rows + entry_reference_rows + cross_reference_rows


def export_reference_fixture(payload: dict[str, Any], *, output_path: str | Path, manifestation_id: int | None = None) -> Path:
    rows = build_index_fixture_rows(payload, manifestation_id=manifestation_id)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path
