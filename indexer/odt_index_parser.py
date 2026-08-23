from __future__ import annotations

import json
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree


TEXT_NS = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
OFFICE_NS = 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'
NS = {'office': OFFICE_NS, 'text': TEXT_NS}

INDEX_TYPE_PERSON = 'P'
INDEX_TYPE_SUBJECT = 'S'
ODT_FILENAME_PATTERNS = ('Index*.odt', 'Sachregister*.odt')
REFERENCE_TYPE_CODES = {'A', 'B', 'F', 'N', 'T', 'V', 'Z'}
PAGE_RELATION_BEFORE = 'before'
PAGE_RELATION_AFTER = 'after'
PAGE_SCOPE_PASSIM = 'passim'
LOCATOR_UNIT_PAGE = 'page'
LOCATOR_UNIT_COLUMN = 'column'
LOCATOR_UNIT_FIGURE = 'figure'
LOCATOR_MARKERS = {
    'S.': LOCATOR_UNIT_PAGE,
    'Sp.': LOCATOR_UNIT_COLUMN,
    'Abb.': LOCATOR_UNIT_FIGURE,
}
REFERENCE_PREFIXES = (
    ('siehe auch ', 'see_also'),
    ('siehe ', 'see'),
    ('vgl. ', 'compare'),
    ('s. ', 'see'),
)


@dataclass(frozen=True)
class PageLocator:
    raw: str
    page_start: int | None
    page_end: int | None
    note: str = ''
    reference_types: tuple[str, ...] = ()
    page_start_relation: str = ''
    page_end_relation: str = ''
    page_scope: str = ''
    locator_unit: str = ''

    @property
    def effective_page_start_relation(self) -> str:
        return self.page_start_relation or 'on'

    @property
    def effective_page_end_relation(self) -> str:
        return self.page_end_relation or 'on'

    def to_dict(self) -> dict:
        payload = {
            'raw': self.raw,
            'page_start': self.page_start,
            'page_end': self.page_end,
            'note': self.note,
            'reference_types': list(self.reference_types),
        }
        if self.page_start_relation:
            payload['page_start_relation'] = self.page_start_relation
        if self.page_end_relation:
            payload['page_end_relation'] = self.page_end_relation
        if self.page_scope:
            payload['page_scope'] = self.page_scope
        if self.locator_unit:
            payload['locator_unit'] = self.locator_unit
        return payload


@dataclass(frozen=True)
class ParsedPageReference:
    kind: str
    document: str
    page_locators: tuple[PageLocator, ...]

    def to_dict(self) -> dict:
        return {
            'kind': self.kind,
            'document': self.document,
            'page_locators': [locator.to_dict() for locator in self.page_locators],
        }


@dataclass(frozen=True)
class ParsedCrossReference:
    kind: str
    marker: str
    target_raw: str
    target_levels: tuple['ParsedLemmaLevel', ...]

    def to_dict(self) -> dict:
        return {
            'kind': self.kind,
            'marker': self.marker,
            'target_raw': self.target_raw,
            'target_levels': [level.to_dict() for level in self.target_levels],
        }


@dataclass(frozen=True)
class ParsedLemmaLevel:
    label: str
    metadata: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            'label': self.label,
            'metadata': list(self.metadata),
        }


@dataclass(frozen=True)
class ParsedIndexEntry:
    index_type: str
    raw_lemma: str
    levels: tuple[ParsedLemmaLevel, ...]
    references: tuple['ParsedReference', ...]

    def to_dict(self) -> dict:
        return {
            'index_type': self.index_type,
            'raw_lemma': self.raw_lemma,
            'levels': [level.to_dict() for level in self.levels],
            'references': [reference.to_dict() for reference in self.references],
        }


class OdtIndexParseError(ValueError):
    pass


ParsedReference = ParsedPageReference | ParsedCrossReference


def iter_index_file_paths(source_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in ODT_FILENAME_PATTERNS:
        paths.extend(source_dir.glob(pattern))
    return sorted({path for path in paths if path.is_file()})


def read_odt_paragraphs(odt_path: Path) -> list[str]:
    with zipfile.ZipFile(odt_path) as archive:
        content_xml = archive.read('content.xml')

    root = ElementTree.fromstring(content_xml)
    paragraphs = []
    for paragraph in root.findall('.//text:p', NS):
        text = _normalize_whitespace(_flatten_text(paragraph)).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def parse_odt_file(odt_path: Path) -> list[ParsedIndexEntry]:
    entries: list[ParsedIndexEntry] = []
    for paragraph in read_odt_paragraphs(odt_path):
        if ':\t' not in paragraph:
            continue
        entries.append(parse_index_paragraph(paragraph, odt_path.name))
    return entries


def parse_index_paragraph(paragraph: str, filename: str = '') -> ParsedIndexEntry:
    raw_paragraph = _normalize_whitespace(paragraph).strip()
    match = re.search(r':\t(?=[^\t]*$)', raw_paragraph)
    if match is None:
        raise OdtIndexParseError(f'Missing lemma/reference separator in paragraph: {paragraph!r}')

    raw_lemma = raw_paragraph[: match.start()].strip()
    raw_references = raw_paragraph[match.end() :].strip()
    if not raw_lemma:
        raise OdtIndexParseError(f'Missing lemma before separator: {paragraph!r}')
    if not raw_references:
        raise OdtIndexParseError(f'Missing references after separator: {paragraph!r}')

    levels = tuple(parse_lemma_levels(raw_lemma))
    references = tuple(parse_references(raw_references))
    index_type = INDEX_TYPE_PERSON if filename.startswith('Index') else INDEX_TYPE_SUBJECT
    return ParsedIndexEntry(
        index_type=index_type,
        raw_lemma=raw_lemma,
        levels=levels,
        references=references,
    )


def parse_lemma_levels(raw_lemma: str) -> list[ParsedLemmaLevel]:
    first_split = _split_top_level(raw_lemma, ',', maxsplit=1)
    levels = [first_split[0]]
    if len(first_split) == 2:
        levels.extend(_split_top_level(first_split[1], ';', maxsplit=1))
    else:
        levels = _split_top_level(raw_lemma, ';', maxsplit=1)

    parsed_levels: list[ParsedLemmaLevel] = []
    for level in levels:
        cleaned = _parse_lemma_level(level)
        if cleaned.label:
            parsed_levels.append(cleaned)

    if not parsed_levels:
        raise OdtIndexParseError(f'Unable to parse lemma levels from: {raw_lemma!r}')
    if len(parsed_levels) > 3:
        raise OdtIndexParseError(f'Too many lemma levels in: {raw_lemma!r}')
    return parsed_levels


def parse_references(raw_references: str) -> list[ParsedReference]:
    parsed: list[ParsedReference] = []
    for chunk in _split_top_level(raw_references.rstrip(';'), ';'):
        reference_text = chunk.strip()
        if not reference_text:
            continue
        try:
            parsed_reference = parse_reference(reference_text)
        except OdtIndexParseError:
            if parsed and isinstance(parsed[-1], ParsedPageReference):
                parsed_reference = parse_reference(reference_text, fallback_document=parsed[-1].document)
            else:
                raise
        parsed.append(parsed_reference)

    if not parsed:
        raise OdtIndexParseError(f'Unable to parse references from: {raw_references!r}')
    return parsed


def parse_reference(reference_text: str, fallback_document: str | None = None) -> ParsedReference:
    reference_text = _normalize_whitespace(reference_text).strip()

    for prefix, kind in REFERENCE_PREFIXES:
        if reference_text.startswith(prefix):
            return parse_cross_reference(reference_text, prefix, kind)

    match = re.match(
        r'^(?P<document>.+),\s*(?:(?P<relation>nach|vor)\s+)?((?P<marker>S\.|Sp\.|Abb\.)\s*(?P<pages>.+)|(?P<passim>passim(?:\s*,\s*.+)?))$',
        reference_text,
    )
    if match is None and fallback_document is not None:
        continuation = re.match(
            r'^(?:(?P<relation>nach|vor)\s+)?(?P<marker>S\.|Sp\.|Abb\.)\s*(?P<pages>.+)$',
            reference_text,
        )
        if continuation is not None:
            match = continuation
    if match is None:
        raise OdtIndexParseError(f'Missing page marker in reference: {reference_text!r}')

    pages_raw = match.group('pages')
    if pages_raw is None and match.group('passim') is not None:
        pages_raw = match.group('passim')
    pages_raw = pages_raw.strip() if pages_raw else ''
    default_relation = _parse_page_relation(match.groupdict().get('relation'))
    default_unit = _parse_locator_unit(match.groupdict().get('marker'))
    locators = tuple(
        parse_page_locators(pages_raw, default_relation=default_relation, default_unit=default_unit)
    )
    return ParsedPageReference(
        kind='page',
        # raw=(f'{fallback_document}, {reference_text}' if 'document' not in match.groupdict() and fallback_document else reference_text),
        document=(match.groupdict().get('document') or fallback_document or '').strip(),
        page_locators=locators,
    )


def parse_cross_reference(reference_text: str, marker: str, kind: str) -> ParsedCrossReference:
    target_raw = reference_text[len(marker) :].strip()
    if not target_raw:
        raise OdtIndexParseError(f'Missing cross-reference target in: {reference_text!r}')

    bracket_match = re.match(r'^\[(?P<target>.*)\]$', target_raw)
    if bracket_match is not None:
        target_raw = bracket_match.group('target').strip()

    if not target_raw:
        raise OdtIndexParseError(f'Missing cross-reference target in: {reference_text!r}')

    return ParsedCrossReference(
        kind=kind,
        marker=marker.strip(),
        target_raw=target_raw,
        target_levels=tuple(parse_lemma_levels(target_raw)),
    )


def parse_page_locators(pages_raw: str, default_relation: str = '', default_unit: str = '') -> list[PageLocator]:
    locators: list[PageLocator] = []
    for token in pages_raw.split(','):
        cleaned = token.strip()
        if not cleaned:
            continue
        locators.append(
            parse_page_locator(cleaned, default_relation=default_relation, default_unit=default_unit)
        )
    return locators


def parse_page_locator(token: str, default_relation: str = '', default_unit: str = '') -> PageLocator:
    normalized = _normalize_whitespace(token).strip()
    locator_unit, normalized = _extract_locator_unit(normalized, default_unit)

    if normalized.casefold() == PAGE_SCOPE_PASSIM:
        return PageLocator(
            raw=token,
            page_start=None,
            page_end=None,
            reference_types=('T',),
            page_scope=PAGE_SCOPE_PASSIM,
            locator_unit=_omit_default_page_unit(locator_unit),
        )

    note_match = re.match(r'^(?P<base>.*?)(?P<note>\([^)]+\))$', token)
    note = ''
    base = normalized
    if note_match:
        base = note_match.group('base').strip()
        note = note_match.group('note')

    reference_types = parse_reference_types(note, has_numeric_locator=bool(re.match(r'^\d+(?:[-/]\d+)?$', base)))
    relation = default_relation if re.match(r'^\d+(?:[-/]\d+)?$', base) else ''

    range_match = re.match(r'^(?P<start>\d+)(?P<sep>[-/])(?P<end>\d+)$', base)
    if range_match:
        start = int(range_match.group('start'))
        end = _resolve_shorthand_end(start, range_match.group('end'))
        return PageLocator(
            raw=token,
            page_start=start,
            page_end=end,
            note=note,
            reference_types=reference_types,
            page_start_relation=relation,
            page_end_relation=relation,
            locator_unit=_omit_default_page_unit(locator_unit),
        )

    if re.match(r'^\d+$', base):
        page = int(base)
        return PageLocator(
            raw=token,
            page_start=page,
            page_end=page,
            note=note,
            reference_types=reference_types,
            page_start_relation=relation,
            page_end_relation=relation,
            locator_unit=_omit_default_page_unit(locator_unit),
        )

    return PageLocator(
        raw=token,
        page_start=None,
        page_end=None,
        note=note,
        reference_types=reference_types,
        locator_unit=_omit_default_page_unit(locator_unit),
    )


def parse_reference_types(note: str, has_numeric_locator: bool) -> tuple[str, ...]:
    if not has_numeric_locator:
        return ()
    if not note:
        return ('T',)

    content = note.strip()[1:-1].strip()
    if not content:
        return ()

    type_codes = tuple(part.strip() for part in content.split('+') if part.strip())
    if type_codes and all(code in REFERENCE_TYPE_CODES for code in type_codes):
        return type_codes
    return ()


def build_document_dictionary(
    entries: Iterable[ParsedIndexEntry],
    *,
    error_sink: list[str] | None = None,
) -> tuple[dict[str, dict], list[dict]]:
    documents: dict[str, dict] = {}
    document_lookup: dict[str, int] = {}
    serialized_entries: list[dict] = []

    def ensure_document(label: str, *, part_of: str | None = None, context_label: str | None = None) -> str:
        label = _resolve_ders_reference(label, context=context_label, error_sink=error_sink)
        normalized = _normalize_document_key(label)
        if not normalized:
            normalized = label.casefold()

        lookup_key = normalized if part_of is None else f'{normalized}::{part_of}'
        if lookup_key not in document_lookup:
            key = str(len(documents))
            payload = {'label': label, 'normalized_label': normalized}
            if part_of is not None:
                payload['part_of'] = part_of
            documents[key] = payload
            document_lookup[lookup_key] = len(documents) - 1

        key = str(document_lookup[lookup_key])
        if part_of is not None and documents.get(key, {}).get('part_of') is None:
            documents[key]['part_of'] = part_of
        return key

    for entry in entries:
        payload = entry.to_dict()
        references: list[dict] = []
        for reference in payload.get('references', []):
            document_label = reference.get('document')
            if isinstance(document_label, str):
                base_label, part_label = _split_document_label(document_label)
                if part_label is not None:
                    base_label = _resolve_ders_reference(base_label, context=part_label, error_sink=error_sink)
                    base_key = ensure_document(base_label)
                    part_key = ensure_document(part_label, part_of=base_key, context_label=base_label)
                    reference['document'] = part_key
                else:
                    reference['document'] = ensure_document(document_label)
            references.append(reference)
        payload['references'] = references
        serialized_entries.append(payload)

    # Sort documents by their normalized labels for consistent output
    sorted_documents = dict(sorted(documents.items(), key=lambda item: item[1]['normalized_label']))
    return sorted_documents, serialized_entries


def dump_entries_as_json(entries: Iterable[ParsedIndexEntry], pretty: bool = False) -> str:
    documents, serialized_entries = build_document_dictionary(entries)
    payload = {'documents': documents, 'entries': serialized_entries}
    if pretty:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return json.dumps(payload, ensure_ascii=False)


def _parse_page_relation(relation_text: str | None) -> str:
    if relation_text == 'nach':
        return PAGE_RELATION_AFTER
    if relation_text == 'vor':
        return PAGE_RELATION_BEFORE
    return ''


def _parse_locator_unit(marker_text: str | None) -> str:
    if marker_text is None:
        return ''
    return LOCATOR_MARKERS.get(marker_text, '')


def _extract_locator_unit(token: str, default_unit: str) -> tuple[str, str]:
    for marker_text, locator_unit in LOCATOR_MARKERS.items():
        prefix = f'{marker_text} '
        if token.startswith(prefix):
            return locator_unit, token[len(prefix) :].strip()
        if token == marker_text:
            return locator_unit, ''
    return default_unit, token


def _omit_default_page_unit(locator_unit: str) -> str:
    if locator_unit == LOCATOR_UNIT_PAGE:
        return ''
    return locator_unit


def _parse_lemma_level(raw_level: str) -> ParsedLemmaLevel:
    metadata = tuple(part.strip() for part in re.findall(r'\(([^()]*)\)', raw_level) if part.strip())
    label = re.sub(r'\([^()]*\)', '', raw_level)
    label = _normalize_whitespace(label).strip(' ,;:')
    return ParsedLemmaLevel(label=label, metadata=metadata)


def _split_top_level(value: str, separator: str, maxsplit: int = -1) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    paren_depth = 0
    bracket_depth = 0
    splits = 0

    for char in value:
        if char == '(':
            paren_depth += 1
        elif char == ')' and paren_depth > 0:
            paren_depth -= 1
        elif char == '[':
            bracket_depth += 1
        elif char == ']' and bracket_depth > 0:
            bracket_depth -= 1

        if char == separator and paren_depth == 0 and bracket_depth == 0 and (maxsplit < 0 or splits < maxsplit):
            parts.append(''.join(current).strip())
            current = []
            splits += 1
            continue
        current.append(char)

    parts.append(''.join(current).strip())
    return parts


def _flatten_text(element: ElementTree.Element) -> str:
    parts: list[str] = []
    if element.text:
        parts.append(element.text)

    for child in element:
        if child.tag == f'{{{TEXT_NS}}}tab':
            parts.append('\t')
        elif child.tag == f'{{{TEXT_NS}}}s':
            count = int(child.attrib.get(f'{{{TEXT_NS}}}c', '1'))
            parts.append(' ' * count)
        elif child.tag == f'{{{TEXT_NS}}}line-break':
            parts.append(' ')
        else:
            parts.append(_flatten_text(child))

        if child.tail:
            parts.append(child.tail)

    return ''.join(parts)


def _normalize_whitespace(value: str) -> str:
    value = value.replace('\u00ad', '')
    value = value.replace('\u00a0', ' ')
    value = re.sub(r'\s*\t\s*', '\t', value)
    value = re.sub(r'[ \r\n\f\v]+', ' ', value)
    return value


def _resolve_ders_reference(document_label: str, *, context: str | None = None, error_sink: list[str] | None = None) -> str:
    if 'Ders.' not in document_label:
        return document_label

    author = _extract_author_prefix(context or document_label)
    if author is None:
        message = f'Unable to resolve Ders. placeholder in document label: {document_label!r}'
        if error_sink is not None:
            error_sink.append(message)
        return document_label

    result = re.sub(r'(?<!\w)Ders\.(?!\w)', author, document_label)
    return result.strip()


def _extract_author_prefix(document_label: str) -> str | None:
    if ':' not in document_label:
        return None
    author = document_label.split(':', 1)[0].strip()
    if not author or author.casefold() == 'ders.':
        return None
    return author


def _normalize_document_key(value: str) -> str:
    normalized = value.casefold()
    for quote in ('“', '”', '„', '‟', '’', '‘', '’', '"', "'", '«', '»'):
        normalized = normalized.replace(quote, '')
    normalized = normalized.replace('-', ' ')
    normalized = re.sub(r'[^\w\s]+', ' ', normalized, flags=re.UNICODE)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()


def _split_document_label(document_label: str) -> tuple[str, str | None]:
    cleaned = document_label.strip()
    if cleaned.lower().startswith('in:'):
        cleaned = cleaned[3:].strip()

    separator = ', in:'
    if separator not in cleaned:
        return cleaned, None

    before, after = cleaned.split(separator, 1)
    before = before.strip()
    after = after.strip()
    if not before or not after:
        return cleaned, None
    return after, before


def _resolve_shorthand_end(start: int, end_text: str) -> int:
    if len(end_text) >= len(str(start)):
        return int(end_text)

    start_prefix = str(start)[: len(str(start)) - len(end_text)]
    candidate = int(f'{start_prefix}{end_text}')
    while candidate < start:
        candidate += 10 ** len(end_text)
    return candidate