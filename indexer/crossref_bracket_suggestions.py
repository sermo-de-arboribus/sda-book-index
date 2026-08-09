from __future__ import annotations

import re
from dataclasses import dataclass


CROSS_REFERENCE_MARKERS = ('siehe auch', 'siehe', 'vgl.', 's.')


@dataclass(frozen=True)
class CrossReferenceBracketSuggestion:
    source: str
    error: str
    marker: str
    original_target: str
    suggested_target: str
    paragraph: str
    suggested_paragraph: str

    def to_text(self) -> str:
        return (
            f'{self.source}\n'
            f'error: {self.error}\n'
            f'marker: {self.marker}\n'
            f'original_target: {self.original_target}\n'
            f'suggested_target: {self.suggested_target}\n'
            f'paragraph: {self.paragraph}\n'
            f'suggested_paragraph: {self.suggested_paragraph}'
        )


def find_bracket_suggestions(error_text: str) -> list[CrossReferenceBracketSuggestion]:
    suggestions: list[CrossReferenceBracketSuggestion] = []
    for block in _split_error_blocks(error_text):
        suggestion = _build_suggestion(block)
        if suggestion is not None:
            suggestions.append(suggestion)
    return suggestions


def format_bracket_suggestions(suggestions: list[CrossReferenceBracketSuggestion]) -> str:
    if not suggestions:
        return ''
    return '\n\n'.join(suggestion.to_text() for suggestion in suggestions) + '\n'


def _split_error_blocks(error_text: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for chunk in re.split(r'\n\s*\n', error_text.strip()):
        lines = [line for line in chunk.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        blocks.append(
            {
                'source': lines[0].strip(),
                'error': lines[1].removeprefix('error: ').strip(),
                'paragraph': lines[2].removeprefix('paragraph: ').strip(),
            }
        )
    return blocks


def _build_suggestion(block: dict[str, str]) -> CrossReferenceBracketSuggestion | None:
    missing_reference = _extract_missing_reference(block['error'])
    if missing_reference is None:
        return None

    paragraph = block['paragraph']
    for marker in CROSS_REFERENCE_MARKERS:
        suggestion = _suggest_for_marker(paragraph, marker, missing_reference)
        if suggestion is None:
            continue
        original_target, suggested_paragraph = suggestion
        return CrossReferenceBracketSuggestion(
            source=block['source'],
            error=block['error'],
            marker=marker,
            original_target=original_target,
            suggested_target=f'[{original_target}]',
            paragraph=paragraph,
            suggested_paragraph=suggested_paragraph,
        )
    return None


def _extract_missing_reference(error: str) -> str | None:
    match = re.fullmatch(r"Missing page marker in reference: '(?P<reference>.*)'", error)
    if match is None:
        return None
    missing_reference = match.group('reference').strip()
    return missing_reference or None


def _suggest_for_marker(paragraph: str, marker: str, missing_reference: str) -> tuple[str, str] | None:
    pattern = re.compile(rf'(?P<prefix>(?:^|\t|;\s*))(?P<marker>{re.escape(marker)})\s+(?!\[)')
    for match in pattern.finditer(paragraph):
        target_start = match.end()
        for separator in ('; ', ';'):
            suffix = f'{separator}{missing_reference}'
            suffix_index = paragraph.find(suffix, target_start)
            if suffix_index == -1:
                continue

            target_end = suffix_index + len(suffix)
            original_target = paragraph[target_start:target_end].strip()
            if not original_target or '[' in original_target or ']' in original_target:
                continue

            suggested_paragraph = (
                paragraph[:target_start] + f'[{original_target}]' + paragraph[target_end:]
            )
            return original_target, suggested_paragraph
    return None