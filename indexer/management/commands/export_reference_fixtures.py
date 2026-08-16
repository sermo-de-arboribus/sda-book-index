from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from indexer.reference_fixtures import export_reference_fixture


class Command(BaseCommand):
    help = 'Export parsed ODT index JSON into Django fixture rows for Reference and ReferenceLocator.'

    def add_arguments(self, parser):
        parser.add_argument('source_json', type=Path, help='Path to the JSON produced by extract_odt_index.')
        parser.add_argument(
            '--output',
            type=Path,
            required=True,
            help='Destination path for the generated fixture JSON file.',
        )
        parser.add_argument(
            '--manifestation-id',
            type=int,
            default=None,
            help='Optional fixed manifestation id to attach every exported reference to. Useful for staging imports before manual review.',
        )

    def handle(self, *args, **options):
        source_path = options['source_json'].expanduser().resolve()
        if not source_path.exists() or not source_path.is_file():
            raise CommandError(f'Input JSON not found: {source_path}')

        payload = json.loads(source_path.read_text(encoding='utf-8'))
        output_path = options['output'].expanduser().resolve()
        export_reference_fixture(payload, output_path=output_path, manifestation_id=options['manifestation_id'])
        self.stdout.write(self.style.SUCCESS(f'Wrote fixture rows to {output_path}'))
