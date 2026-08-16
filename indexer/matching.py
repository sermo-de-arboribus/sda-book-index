from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

from django.db.models import QuerySet

from .models import Manifestation

_TITLE_STOPWORDS = {
    'der', 'die', 'und', 'das', 'ein', 'eine', 'mit', 'zu', 'zur', 'zum', 'im', 'in', 'auf', 'von',
    'des', 'dem', 'den', 'als', 'aus', 'für', 'for', 'the', 'a', 'an', 'of', 'to', 'and', 'or',
}


@dataclass
class ManifestationMatch:
    manifestation: Manifestation
    score: int
    match_type: str
    details: dict


def normalize_title(value: str) -> str:
    if value is None:
        return ''
    value = unicodedata.normalize('NFKD', value)
    value = value.encode('ascii', 'ignore').decode('ascii')
    value = value.lower()
    value = value.replace('’', "'")
    value = re.sub(r"[\W_]+", ' ', value)
    value = re.sub(r'\s+', ' ', value).strip()
    tokens = [token for token in value.split(' ') if token and token not in _TITLE_STOPWORDS]
    return ' '.join(tokens)


def _title_similarity(title_a: str, title_b: str) -> int:
    norm_a = normalize_title(title_a)
    norm_b = normalize_title(title_b)
    if not norm_a or not norm_b:
        return 0
    if norm_a == norm_b:
        return 100
    a_tokens = set(norm_a.split())
    b_tokens = set(norm_b.split())
    if not a_tokens or not b_tokens:
        return 0
    overlap = len(a_tokens & b_tokens)
    total = len(a_tokens | b_tokens)
    if total == 0:
        return 0
    return int((overlap / total) * 100)


def _isbn_match(reference_text: str, manifestation: Manifestation) -> int:
    candidate = (manifestation.isbn_issn or '').strip()
    if not candidate:
        return 0
    cleaned = re.sub(r'[^0-9Xx]', '', candidate)
    if not cleaned:
        return 0
    ref_cleaned = re.sub(r'[^0-9Xx]', '', reference_text or '')
    if not ref_cleaned:
        return 0
    return 90 if cleaned in ref_cleaned or ref_cleaned in cleaned else 0


def suggest_manifestation_matches(
    reference,
    candidate_queryset: QuerySet | Iterable[Manifestation],
    *,
    max_candidates: int = 5,
    min_score: int = 60,
) -> list[ManifestationMatch]:
    """Return ranked candidate manifestations for a parsed reference record."""
    if reference is None:
        return []

    reference_text = reference.raw_document or reference.raw_reference or ''
    container_text = getattr(reference, 'raw_document_part_of', '') or ''
    candidates: list[ManifestationMatch] = []
    qs = list(candidate_queryset)

    for manifestation in qs:
        score = 0
        details: dict = {}
        title_value = manifestation.canonical_title or ''

        if container_text:
            container_similarity = _title_similarity(container_text, title_value)
            if container_similarity:
                score += min(container_similarity, 40)
                details['container_similarity'] = container_similarity
                details['container_title'] = container_text

        isbn_score = _isbn_match(reference_text, manifestation)
        if isbn_score:
            score += isbn_score
            details['isbn_match'] = True

        title_score = _title_similarity(reference_text, title_value)
        if title_score:
            score += min(title_score, 55)
            details['title_similarity'] = title_score

        if manifestation.year and getattr(reference, 'source_year', None):
            if manifestation.year == int(reference.source_year):
                score += 15
                details['year_match'] = True

        if title_value and normalize_title(reference_text) and normalize_title(reference_text) == normalize_title(title_value):
            score += 25
            details['exact_title_match'] = True

        if score >= min_score:
            candidates.append(
                ManifestationMatch(
                    manifestation=manifestation,
                    score=min(score, 100),
                    match_type='isbn' if isbn_score else 'title',
                    details=details,
                )
            )

    candidates.sort(key=lambda item: (-item.score, item.manifestation.slug))
    return candidates[:max_candidates]
