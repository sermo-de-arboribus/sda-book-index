from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def build_reference_fixture_rows(payload: dict[str, Any], *, manifestation_id: int | None = None) -> list[dict[str, Any]]:
    """Build Django fixture rows for Reference and ReferenceLocator objects from parsed ODT output.

    This creates a fixture-friendly payload that can be ingested with `loaddata`, while keeping
    unresolved manifestion links deliberately unset until manual review.

    The parsed document graph can include hierarchical relationships such as a chapter/article
    being part of a larger book or container. These are serialized alongside the raw document so
    later import and matching stages can use the publication context even before a final
    manifestation-to-reference linkage is confirmed.
    """
    rows: list[dict[str, Any]] = []
    documents = payload.get('documents', {}) or {}
    entries = payload.get('entries', []) or []

    for entry_index, entry in enumerate(entries, start=1):
        references = entry.get('references', []) or []
        for ref_index, reference in enumerate(references, start=1):
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
                    'reference_type_codes': ''.join(locator.get('reference_types', [])) or '',
                }
                rows.append({
                    'model': 'indexer.referencelocator',
                    'pk': reference_pk * 10 + locator_index,
                    'fields': locator_fields,
                })

    return rows


def export_reference_fixture(payload: dict[str, Any], *, output_path: str | Path, manifestation_id: int | None = None) -> Path:
    rows = build_reference_fixture_rows(payload, manifestation_id=manifestation_id)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path
