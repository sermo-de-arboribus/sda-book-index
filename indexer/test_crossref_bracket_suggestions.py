from __future__ import annotations

import unittest

from indexer.crossref_bracket_suggestions import find_bracket_suggestions, format_bracket_suggestions


class CrossReferenceBracketSuggestionTests(unittest.TestCase):
    def test_suggests_brackets_for_simple_see_target_with_semicolon(self):
        error_text = (
            'Index A.odt:4342\n'
            "error: Missing page marker in reference: 'Perseus und'\n"
            'paragraph: Andromeda; Befreiung durch Perseus:\ts. Andromeda; Perseus und\n'
        )

        suggestions = find_bracket_suggestions(error_text)

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].marker, 's.')
        self.assertEqual(suggestions[0].original_target, 'Andromeda; Perseus und')
        self.assertEqual(
            suggestions[0].suggested_paragraph,
            'Andromeda; Befreiung durch Perseus:\ts. [Andromeda; Perseus und]',
        )

    def test_suggests_brackets_for_siehe_target_with_semicolon(self):
        error_text = (
            'Index A.odt:6701\n'
            "error: Missing page marker in reference: 'Läden in Paris fotografiert von'\n"
            'paragraph: Atget, Eugène; Pariser Läden fotografiert von:\tsiehe Atget, Eugène; Läden in Paris fotografiert von\n'
        )

        suggestions = find_bracket_suggestions(error_text)

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].marker, 'siehe')
        self.assertEqual(suggestions[0].suggested_target, '[Atget, Eugène; Läden in Paris fotografiert von]')

    def test_ignores_non_cross_reference_errors(self):
        error_text = (
            'Index A.odt:6533\n'
            "error: Missing page marker in reference: 'Voßkamp, W: „Literaturwissenschaft und Kulturwissenchaft” S. 187, 190'\n"
            'paragraph: Assmann, Aleida:\tVoßkamp, W: „Literaturwissenschaft und Kulturwissenchaft” S. 187, 190\n'
        )

        suggestions = find_bracket_suggestions(error_text)

        self.assertEqual(suggestions, [])

    def test_formats_multiple_suggestions(self):
        error_text = (
            'Index A.odt:4342\n'
            "error: Missing page marker in reference: 'Perseus und'\n"
            'paragraph: Andromeda; Befreiung durch Perseus:\ts. Andromeda; Perseus und\n\n'
            'Index A.odt:6701\n'
            "error: Missing page marker in reference: 'Läden in Paris fotografiert von'\n"
            'paragraph: Atget, Eugène; Pariser Läden fotografiert von:\tsiehe Atget, Eugène; Läden in Paris fotografiert von\n'
        )

        report = format_bracket_suggestions(find_bracket_suggestions(error_text))

        self.assertIn('suggested_paragraph: Andromeda; Befreiung durch Perseus:\ts. [Andromeda; Perseus und]', report)
        self.assertIn('suggested_paragraph: Atget, Eugène; Pariser Läden fotografiert von:\tsiehe [Atget, Eugène; Läden in Paris fotografiert von]', report)


if __name__ == '__main__':
    unittest.main()