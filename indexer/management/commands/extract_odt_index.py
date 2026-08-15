from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from indexer.odt_index_parser import (
    OdtIndexParseError,
    build_document_dictionary,
    iter_index_file_paths,
    parse_index_paragraph,
    read_odt_paragraphs,
)

class Command(BaseCommand):
    help = 'Extract index entries from ODT files named Index*.odt or Sachregister*.odt.'

    def add_arguments(self, parser):
        parser.add_argument('source_dir', type=Path, help='Directory containing the ODT source files.')
        parser.add_argument('--output', type=Path, help='Optional JSON output path.')
        parser.add_argument(
            '--error-output',
            type=Path,
            help='Optional text output path for paragraphs that could not be parsed.',
        )
        parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output.')
        parser.add_argument(
            '--limit',
            type=int,
            help='Optional limit for parsed entries, useful for spot checks during parser development.',
        )
        parser.add_argument(
            '--fail-on-error',
            action='store_true',
            help='Abort on the first paragraph that cannot be parsed.',
        )

    def handle(self, *args, **options):
        source_dir = options['source_dir'].expanduser().resolve()
        output_path = options.get('output')
        error_output_path = options.get('error_output')
        pretty = options['pretty']
        limit = options.get('limit')
        fail_on_error = options['fail_on_error']

        if not source_dir.exists() or not source_dir.is_dir():
            raise CommandError(f'Source directory does not exist: {source_dir}')

        odt_files = iter_index_file_paths(source_dir)
        if not odt_files:
            raise CommandError(f'No matching ODT files found under {source_dir}')

        entries: list[dict] = []
        parsed_entries: list = []
        errors: list[str] = []

        for odt_path in odt_files:
            paragraphs = read_odt_paragraphs(odt_path)
            for paragraph_number, paragraph in enumerate(paragraphs, start=1):
                if ':\t' not in paragraph:
                    message = _format_error_record(odt_path, paragraph_number, paragraph, 'Missing colon-tab separator')
                    errors.append(message)
                    continue
                try:
                    parsed = parse_index_paragraph(paragraph, odt_path.name)
                except OdtIndexParseError as exc:
                    message = _format_error_record(odt_path, paragraph_number, paragraph, str(exc))
                    if fail_on_error:
                        raise CommandError(message) from exc
                    errors.append(message)
                    continue

                parsed_entries.append(parsed)
                entries.append(
                    {
                        'source_file': odt_path.name,
                        'source_path': str(odt_path),
                        'paragraph_number': paragraph_number,
                        **parsed.to_dict(),
                    }
                )
                if limit is not None and len(entries) >= limit:
                    break

            if limit is not None and len(entries) >= limit:
                break

        documents, serialized_entries = build_document_dictionary(parsed_entries)
        payload = {
            'source_dir': str(source_dir),
            'source_files': [str(path) for path in odt_files],
            'document_count': len(documents),
            'entry_count': len(serialized_entries),
            'error_count': len(errors),
            'documents': documents,
            'entries': serialized_entries,
        }

        json_text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None)
        if output_path is not None:
            output_path = output_path.expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json_text + ('\n' if pretty else ''), encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f'Wrote {len(entries)} entries to {output_path}'))
        else:
            self.stdout.write(json_text)

        if error_output_path is not None:
            error_output_path = error_output_path.expanduser().resolve()
            error_output_path.parent.mkdir(parents=True, exist_ok=True)
            error_text = '\n\n'.join(errors)
            if error_text:
                error_text += '\n'
            error_output_path.write_text(error_text, encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f'Wrote {len(errors)} parse errors to {error_output_path}'))

        if errors:
            self.stderr.write(self.style.WARNING(f'Skipped {len(errors)} paragraphs with parse errors.'))
            for message in errors[:20]:
                self.stderr.write(message)
            if len(errors) > 20:
                self.stderr.write(f'... and {len(errors) - 20} more errors.')


def _format_error_record(odt_path: Path, paragraph_number: int, paragraph: str, error: str) -> str:
    return (
        f'{odt_path.name}:{paragraph_number}\n'
        f'error: {error}\n'
        f'paragraph: {paragraph}'
    )
