from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from indexer.crossref_bracket_suggestions import format_bracket_suggestions, find_bracket_suggestions


class Command(BaseCommand):
    help = 'Find old s./siehe cross-references with semicolons and suggest bracketed targets.'

    def add_arguments(self, parser):
        parser.add_argument(
            'error_file',
            nargs='?',
            type=Path,
            default=Path('odt-parse-errors.txt'),
            help='Path to the parse-error report produced by extract_odt_index.',
        )
        parser.add_argument('--output', type=Path, help='Optional output path for the suggestion report.')

    def handle(self, *args, **options):
        error_file = options['error_file'].expanduser().resolve()
        output_path = options.get('output')

        if not error_file.exists() or not error_file.is_file():
            raise CommandError(f'Error file does not exist: {error_file}')

        error_text = error_file.read_text(encoding='utf-8')
        suggestions = find_bracket_suggestions(error_text)
        report_text = format_bracket_suggestions(suggestions)

        if output_path is not None:
            output_path = output_path.expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_text, encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f'Wrote {len(suggestions)} suggestions to {output_path}'))
        else:
            self.stdout.write(report_text)

        if not suggestions:
            self.stdout.write('No bracket suggestions found.')