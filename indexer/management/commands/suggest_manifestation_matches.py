from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from indexer.matching import suggest_manifestation_matches
from indexer.models import Manifestation, ManifestationSuggestion, Reference


class Command(BaseCommand):
    help = 'Generate ranked manifestation suggestions for parsed reference records and store them reviewably.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reference-id',
            type=int,
            help='Optional specific Reference id to score against all manifestations.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Maximum suggestions per reference.',
        )
        parser.add_argument(
            '--min-score',
            type=int,
            default=60,
            help='Minimum score threshold for a suggestion to be kept.',
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Delete previously stored suggestion rows for the selected references before creating new ones.',
        )
        parser.add_argument(
            '--output',
            type=Path,
            help='Optional path to write the generated suggestions as JSON.',
        )

    def handle(self, *args, **options):
        reference_id = options.get('reference_id')
        limit = options['limit']
        min_score = options['min_score']
        clear_existing = options['clear_existing']
        output_path = options.get('output')

        queryset = Reference.objects.select_related('manifestation').all()
        if reference_id is not None:
            queryset = queryset.filter(pk=reference_id)
            if not queryset.exists():
                raise CommandError(f'Reference not found for id={reference_id}')

        if not queryset.exists():
            self.stdout.write('No references found to score.')
            return

        all_manifestations = Manifestation.objects.all()
        output_rows = []
        stored_count = 0

        for reference in queryset:
            if clear_existing:
                ManifestationSuggestion.objects.filter(reference=reference).delete()

            matches = suggest_manifestation_matches(
                reference,
                all_manifestations,
                max_candidates=limit,
                min_score=min_score,
            )
            for match in matches:
                suggestion, created = ManifestationSuggestion.objects.update_or_create(
                    reference=reference,
                    manifestation=match.manifestation,
                    defaults={
                        'score': match.score,
                        'match_type': match.match_type,
                        'status': ManifestationSuggestion.STATUS_SUGGESTED,
                        'details': match.details,
                    },
                )
                stored_count += 1
                output_rows.append(
                    {
                        'reference_id': reference.pk,
                        'reference_document': reference.raw_document,
                        'manifestation_id': match.manifestation.pk,
                        'manifestation_slug': match.manifestation.slug,
                        'canonical_title': match.manifestation.canonical_title,
                        'score': suggestion.score,
                        'match_type': suggestion.match_type,
                        'status': suggestion.status,
                        'details': suggestion.details,
                        'created': created,
                    }
                )

        if output_path is not None:
            output_path = output_path.expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(output_rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f'Wrote {len(output_rows)} suggestions to {output_path}'))
        else:
            self.stdout.write(json.dumps(output_rows, ensure_ascii=False, indent=2))

        self.stdout.write(f'Generated and stored {stored_count} suggestion rows.')
