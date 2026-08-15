from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from indexer.odt_index_parser import (
    OdtIndexParseError,
    build_document_dictionary,
    iter_index_file_paths,
    parse_index_paragraph,
    parse_page_locator,
    parse_reference,
    read_odt_paragraphs,
)


class OdtIndexParserTests(unittest.TestCase):
    def test_parse_index_paragraph_with_three_levels_and_metadata(self):
        entry = parse_index_paragraph(
            'Aachen, Hans von (dt. Maler, 1552-1615); Aufträge Rudolfs II.:\t'
            'Blom, P.: „Sammelwunder, Sammelwahn“, S. 69, 71; '
            'Nestler, G.: „Orlando di Lasso“, in: Fassmann, K. (Hg.): „Die Großen“, Bd. V, S. 167, 169(A);'
        )

        self.assertEqual([level.label for level in entry.levels], ['Aachen', 'Hans von', 'Aufträge Rudolfs II.'])
        self.assertEqual(entry.levels[1].metadata, ('dt. Maler, 1552-1615',))
        self.assertEqual(len(entry.references), 2)
        self.assertEqual(entry.references[0].document, 'Blom, P.: „Sammelwunder, Sammelwahn“')
        self.assertEqual(entry.references[0].page_locators[0].page_start, 69)
        self.assertEqual(entry.references[0].page_locators[0].reference_types, ('T',))
        self.assertEqual(entry.references[1].page_locators[1].note, '(A)')
        self.assertEqual(entry.references[1].page_locators[1].reference_types, ('A',))

    def test_parse_reference_uses_last_page_marker(self):
        reference = parse_reference(
            'Arnoldi, E. F.: „Marc Chagall“, in: Fassmann, K. (Hg.): „Die Großen“, Bd. X, S. 370, 376'
        )

        self.assertEqual(reference.kind, 'page')
        self.assertEqual(
            reference.document,
            'Arnoldi, E. F.: „Marc Chagall“, in: Fassmann, K. (Hg.): „Die Großen“, Bd. X',
        )
        self.assertEqual(reference.page_locators[1].page_start, 376)
        self.assertEqual(reference.page_locators[0].effective_page_start_relation, 'on')

    def test_parse_reference_supports_after_page_relation(self):
        reference = parse_reference('Meerwald, A.: „Das Schloß B.-Krumau“, nach S. 64(B)')

        self.assertEqual(reference.kind, 'page')
        self.assertEqual(reference.document, 'Meerwald, A.: „Das Schloß B.-Krumau“')
        self.assertEqual(reference.page_locators[0].page_start, 64)
        self.assertEqual(reference.page_locators[0].page_start_relation, 'after')
        self.assertEqual(reference.page_locators[0].page_end_relation, 'after')
        self.assertEqual(reference.page_locators[0].reference_types, ('B',))

    def test_parse_reference_supports_column_marker(self):
        reference = parse_reference('Habermas, J.: „Um uns als Selbsttäuscher zu entlarven, bedarf es mehr“, Sp. 2')

        self.assertEqual(reference.kind, 'page')
        self.assertEqual(reference.page_locators[0].page_start, 2)
        self.assertEqual(reference.page_locators[0].locator_unit, 'column')

    def test_parse_reference_supports_figure_marker(self):
        reference = parse_reference('Ewing, W. A.: “Blumenfeld. A Fetish for Beauty”, Abb. 125')

        self.assertEqual(reference.kind, 'page')
        self.assertEqual(reference.page_locators[0].page_start, 125)
        self.assertEqual(reference.page_locators[0].locator_unit, 'figure')

    def test_parse_reference_supports_marker_continuation_after_semicolon(self):
        entry = parse_index_paragraph(
            'van Cleef & Arpels:\tEwing, W. A.: “Blumenfeld. A Fetish for Beauty”, S. 97, 103; Abb. 135'
        )

        self.assertEqual(len(entry.references), 2)
        self.assertEqual(entry.references[0].document, 'Ewing, W. A.: “Blumenfeld. A Fetish for Beauty”')
        self.assertEqual(entry.references[1].document, 'Ewing, W. A.: “Blumenfeld. A Fetish for Beauty”')
        self.assertEqual(entry.references[1].page_locators[0].page_start, 135)
        self.assertEqual(entry.references[1].page_locators[0].locator_unit, 'figure')

    def test_parse_reference_supports_before_page_relation(self):
        reference = parse_reference('Beispiel: „Unpaginiert“, vor S. 64(B)')

        self.assertEqual(reference.page_locators[0].page_start_relation, 'before')
        self.assertEqual(reference.page_locators[0].page_end_relation, 'before')

    def test_parse_reference_supports_passim_without_page_marker(self):
        reference = parse_reference('Aggeler, J.: „Der Weg von Kleists Alkmene“, passim')

        self.assertEqual(reference.kind, 'page')
        self.assertEqual(reference.document, 'Aggeler, J.: „Der Weg von Kleists Alkmene“')
        self.assertEqual(reference.page_locators[0].page_scope, 'passim')
        self.assertEqual(reference.page_locators[0].reference_types, ('T',))

    def test_build_document_dictionary_normalizes_and_deduplicates_documents(self):
        entries = (
            parse_index_paragraph('A:	Herder, J. G.: „Sämmtliche Werke“, S. 33'),
            parse_index_paragraph('B:	Herder, J. G.: "Sämmtliche Werke", S. 20; Herder, J. G.: "Sämmtliche Werke", Abb. 12'),
        )

        documents, serialized_entries = build_document_dictionary(entries)

        self.assertEqual(list(documents.keys()), ['0'])
        self.assertEqual(documents['0']['label'], 'Herder, J. G.: „Sämmtliche Werke“')
        self.assertEqual(serialized_entries[0]['references'][0]['document'], 0)
        self.assertEqual(serialized_entries[1]['references'][0]['document'], 0)
        self.assertEqual(serialized_entries[1]['references'][1]['document'], 0)

    def test_parse_reference_supports_passim_with_trailing_note(self):
        reference = parse_reference('Plautus: „Amphitruo“, passim, bes. 147ff (Nachwort)')

        self.assertEqual(reference.page_locators[0].page_scope, 'passim')
        self.assertEqual(reference.page_locators[1].raw, 'bes. 147ff (Nachwort)')

    def test_parse_reference_ignores_initials_before_title_then_passim(self):
        entry = parse_index_paragraph(
            'Komplexitätstheorie:\tAaronson, S.: “Why Philosophers Should Care about Computational Complexity”, passim; '
            'Fröba/Wassermann: „Die bedeutendsten Mathematiker“, S. 250; '
            'Sipser, M.: „Introduction to the Theory of Computation“, S. 2, 155/56, 253'
        )

        self.assertEqual(entry.references[0].document, 'Aaronson, S.: “Why Philosophers Should Care about Computational Complexity”')
        self.assertEqual(entry.references[0].page_locators[0].page_scope, 'passim')

    def test_parse_reference_supports_cross_reference(self):
        reference = parse_reference('s. Abd al-Karim, Mohammed')

        self.assertEqual(reference.kind, 'see')
        self.assertEqual(reference.marker, 's.')
        self.assertEqual(reference.target_raw, 'Abd al-Karim, Mohammed')
        self.assertEqual([level.label for level in reference.target_levels], ['Abd al-Karim', 'Mohammed'])

    def test_parse_reference_supports_siehe_and_vgl_cross_references(self):
        reference = parse_reference('siehe Albertus Magnus')
        self.assertEqual(reference.kind, 'see')
        self.assertEqual(reference.marker, 'siehe')
        self.assertEqual(reference.target_raw, 'Albertus Magnus')

        reference = parse_reference('vgl. Aphros')
        self.assertEqual(reference.kind, 'compare')
        self.assertEqual(reference.marker, 'vgl.')
        self.assertEqual(reference.target_raw, 'Aphros')

        reference = parse_reference('siehe auch Alliacus')
        self.assertEqual(reference.kind, 'see_also')
        self.assertEqual(reference.marker, 'siehe auch')
        self.assertEqual(reference.target_raw, 'Alliacus')

        reference = parse_reference('siehe [Andromeda; Perseus und]')
        self.assertEqual(reference.kind, 'see')
        self.assertEqual(reference.target_raw, 'Andromeda; Perseus und')
        self.assertEqual([level.label for level in reference.target_levels], ['Andromeda', 'Perseus und'])

    def test_parse_reference_removes_soft_hyphen_from_raw_and_document(self):
        reference = parse_reference('Her\u00adder, J. G.: „Sämmt\u00adliche Werke“, S. 33(F)')

        self.assertEqual(reference.document, 'Herder, J. G.: „Sämmtliche Werke“')

    def test_parse_page_locator_supports_ranges_and_shorthand(self):
        locator = parse_page_locator('598/99')
        self.assertEqual((locator.page_start, locator.page_end), (598, 599))
        self.assertEqual(locator.reference_types, ('T',))
        self.assertEqual(locator.page_start_relation, '')

        locator = parse_page_locator('67-69')
        self.assertEqual((locator.page_start, locator.page_end), (67, 69))
        self.assertEqual(locator.reference_types, ('T',))

        locator = parse_page_locator('140(T+B)')
        self.assertEqual((locator.page_start, locator.page_end), (140, 140))
        self.assertEqual(locator.reference_types, ('T', 'B'))

        locator = parse_page_locator('444(Z)')
        self.assertEqual((locator.page_start, locator.page_end), (444, 444))
        self.assertEqual(locator.reference_types, ('Z',))

        locator = parse_page_locator('Sp. 1/2')
        self.assertEqual((locator.page_start, locator.page_end), (1, 2))
        self.assertEqual(locator.locator_unit, 'column')

        locator = parse_page_locator('Abb. 52')
        self.assertEqual((locator.page_start, locator.page_end), (52, 52))
        self.assertEqual(locator.locator_unit, 'figure')

        locator = parse_page_locator('Abb. n. S. 480')
        self.assertEqual((locator.page_start, locator.page_end), (None, None))
        self.assertEqual(locator.locator_unit, 'figure')

        locator = parse_page_locator('64(B)', default_relation='after')
        self.assertEqual(locator.page_start_relation, 'after')
        self.assertEqual(locator.page_end_relation, 'after')

        locator = parse_page_locator('passim')
        self.assertEqual((locator.page_start, locator.page_end), (None, None))
        self.assertEqual(locator.page_scope, 'passim')
        self.assertEqual(locator.reference_types, ('T',))

        locator = parse_page_locator('12.9')
        self.assertEqual((locator.page_start, locator.page_end), (None, None))
        self.assertEqual(locator.reference_types, ())

        locator = parse_page_locator('63 (Zitat)')
        self.assertEqual((locator.page_start, locator.page_end), (63, 63))
        self.assertEqual(locator.reference_types, ())

    def test_read_odt_paragraphs_flattens_tabs_and_spans(self):
        content_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <office:document-content
            xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
            xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
          <office:body>
            <office:text>
              <text:p>Aalto, Alvar <text:span>(finn. Architekt, 1898-1976)</text:span>:<text:tab/>Knoller, R.: „Finnland“, S. 124</text:p>
            </office:text>
          </office:body>
        </office:document-content>'''

        with tempfile.TemporaryDirectory() as temp_dir:
            odt_path = Path(temp_dir) / 'Index A.odt'
            with zipfile.ZipFile(odt_path, 'w') as archive:
                archive.writestr('content.xml', content_xml)

            paragraphs = read_odt_paragraphs(odt_path)

        self.assertEqual(
            paragraphs,
            ['Aalto, Alvar (finn. Architekt, 1898-1976):\tKnoller, R.: „Finnland“, S. 124'],
        )

    def test_iter_index_file_paths_filters_supported_prefixes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / 'Index A.odt').write_text('x', encoding='utf-8')
            (root / 'Sachregister A-C.odt').write_text('x', encoding='utf-8')
            (root / 'Andere.odt').write_text('x', encoding='utf-8')

            paths = iter_index_file_paths(root)

        self.assertEqual([path.name for path in paths], ['Index A.odt', 'Sachregister A-C.odt'])

    def test_parse_index_paragraph_requires_tab_separator(self):
        with self.assertRaises(OdtIndexParseError):
            parse_index_paragraph('Kein Parser ohne Tab')

    def test_parse_index_paragraph_with_semicolon_without_comma(self):
        entry = parse_index_paragraph(
            'A Fei; Konzerte veranstaltet von:\tSharp, E.: „Feedback“, S. 227/28'
        )

        self.assertEqual([level.label for level in entry.levels], ['A Fei', 'Konzerte veranstaltet von'])

    def test_parse_index_paragraph_with_cross_reference(self):
        entry = parse_index_paragraph('Abd el-Krim:\ts. Abd al-Karim, Mohammed')

        self.assertEqual([level.label for level in entry.levels], ['Abd el-Krim'])
        self.assertEqual(entry.references[0].kind, 'see')
        self.assertEqual(entry.references[0].target_raw, 'Abd al-Karim, Mohammed')

    def test_parse_index_paragraph_with_siehe_cross_reference(self):
        entry = parse_index_paragraph('Aglaja (in Dostoevskijs Idiot):\tsiehe Epancina, Aglaja')

        self.assertEqual([level.label for level in entry.levels], ['Aglaja'])
        self.assertEqual(entry.references[0].kind, 'see')
        self.assertEqual(entry.references[0].target_raw, 'Epancina, Aglaja')

    def test_parse_index_paragraph_with_bracketed_cross_reference_target(self):
        entry = parse_index_paragraph('Andromeda; Befreiung durch Perseus:\tsiehe [Andromeda; Perseus und]')

        self.assertEqual([level.label for level in entry.levels], ['Andromeda', 'Befreiung durch Perseus'])
        self.assertEqual(len(entry.references), 1)
        self.assertEqual(entry.references[0].kind, 'see')
        self.assertEqual(entry.references[0].target_raw, 'Andromeda; Perseus und')

    def test_page_locator_dict_omits_default_on_relation(self):
        locator = parse_page_locator('64(B)')
        payload = locator.to_dict()

        self.assertNotIn('page_start_relation', payload)
        self.assertNotIn('page_end_relation', payload)

        locator = parse_page_locator('64(B)', default_relation='after')
        payload = locator.to_dict()
        self.assertEqual(payload['page_start_relation'], 'after')
        self.assertEqual(payload['page_end_relation'], 'after')

        locator = parse_page_locator('passim')
        payload = locator.to_dict()
        self.assertEqual(payload['page_scope'], 'passim')

        locator = parse_page_locator('Sp. 2')
        payload = locator.to_dict()
        self.assertEqual(payload['locator_unit'], 'column')

        locator = parse_page_locator('S. 2')
        payload = locator.to_dict()
        self.assertNotIn('locator_unit', payload)


if __name__ == '__main__':
    unittest.main()