from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from .matching import normalize_title, suggest_manifestation_matches
from .models import (
    Agent,
    AgentName,
    ContributorRole,
    IndexEntry,
    IndexEntryCrossReference,
    IndexEntryLabel,
    IndexEntryReference,
    Manifestation,
    ManifestationContribution,
    ManifestationSuggestion,
    ManifestationTitle,
    PersonIdentifier,
    Reference,
    ReferenceLocator,
    Work,
    WorkContribution,
    WorkTitle,
)


class WorkModelTests(TestCase):
    def test_create_book_work(self):
        w = Work.objects.create(slug='my-book', work_type=Work.BOOK, canonical_title='My Book')
        self.assertEqual(w.work_type, 'book')
        self.assertIsNone(w.parent)

    def test_str_uses_english_title(self):
        w = Work.objects.create(slug='test', work_type=Work.BOOK, canonical_title='Fallback')
        WorkTitle.objects.create(id='test-de', work=w, language='de', label='Deutsches Buch')
        WorkTitle.objects.create(id='test-en', work=w, language='en', label='English Book')
        self.assertEqual(str(w), 'English Book')

    def test_str_falls_back_to_canonical_title(self):
        w = Work.objects.create(slug='no-titles', work_type=Work.BOOK, canonical_title='Canonical')
        self.assertEqual(str(w), 'Canonical')

    def test_str_falls_back_to_slug(self):
        w = Work.objects.create(slug='bare-slug', work_type=Work.BOOK)
        self.assertEqual(str(w), 'bare-slug')

    def test_chapter_with_parent(self):
        book = Work.objects.create(slug='book', work_type=Work.BOOK, canonical_title='Book')
        chapter = Work.objects.create(
            slug='chapter-1', work_type=Work.CHAPTER, canonical_title='Chapter 1', parent=book
        )
        self.assertEqual(chapter.parent, book)
        self.assertIn(chapter, book.parts.all())

    def test_work_type_choices(self):
        for wt, _ in Work.WORK_TYPE_CHOICES:
            w = Work.objects.create(slug=f'work-{wt}', work_type=wt, canonical_title=wt)
            self.assertEqual(w.work_type, wt)


class WorkTitleModelTests(TestCase):
    def setUp(self):
        self.work = Work.objects.create(slug='titled-work', work_type=Work.BOOK, canonical_title='T')

    def test_create_title(self):
        t = WorkTitle.objects.create(id='work-title-en', work=self.work, language='en', label='Titled Work')
        self.assertEqual(str(t), 'Titled Work (en)')
        self.assertEqual(t.pk, 'work-title-en')

    def test_unique_together(self):
        WorkTitle.objects.create(id='dup-1', work=self.work, language='en', label='Dup')
        with self.assertRaises(IntegrityError):
            WorkTitle.objects.create(id='dup-2', work=self.work, language='en', label='Dup')

    def test_sort_key_optional(self):
        t = WorkTitle.objects.create(id='opus-la', work=self.work, language='la', label='Opus')
        self.assertEqual(t.sort_key, '')


class AgentModelTests(TestCase):
    def test_create_person_agent(self):
        a = Agent.objects.create(slug='jane-doe', agent_type=Agent.PERSON, canonical_name='Jane Doe')
        self.assertEqual(a.agent_type, 'person')
        self.assertEqual(a.canonical_name, 'Jane Doe')

    def test_create_corporation_agent(self):
        a = Agent.objects.create(slug='acme-corp', agent_type=Agent.CORPORATION, canonical_name='ACME Corp')
        self.assertEqual(a.agent_type, 'corporation')

    def test_str_uses_english_name(self):
        a = Agent.objects.create(slug='agent-test', canonical_name='Fallback')
        AgentName.objects.create(agent=a, language='de', label='Deutsch')
        AgentName.objects.create(agent=a, language='en', label='English Name')
        self.assertEqual(str(a), 'English Name')

    def test_str_falls_back_to_canonical_name(self):
        a = Agent.objects.create(slug='no-names', canonical_name='Canonical Name')
        self.assertEqual(str(a), 'Canonical Name')

    def test_str_falls_back_to_slug(self):
        a = Agent.objects.create(slug='bare-agent')
        self.assertEqual(str(a), 'bare-agent')


class AgentNameModelTests(TestCase):
    def setUp(self):
        self.agent = Agent.objects.create(slug='named-agent', canonical_name='X')

    def test_create_name(self):
        n = AgentName.objects.create(agent=self.agent, language='en', label='Full Name')
        self.assertEqual(str(n), 'Full Name (en)')

    def test_sort_key_optional(self):
        n = AgentName.objects.create(agent=self.agent, language='la', label='Nomen')
        self.assertEqual(n.sort_key, '')

    def test_unique_together(self):
        AgentName.objects.create(agent=self.agent, language='en', label='Dup')
        with self.assertRaises(IntegrityError):
            AgentName.objects.create(agent=self.agent, language='en', label='Dup')


class PersonIdentifierModelTests(TestCase):
    def setUp(self):
        self.person = Agent.objects.create(
            slug='person-agent', agent_type=Agent.PERSON, canonical_name='Person Agent'
        )
        self.corporation = Agent.objects.create(
            slug='corp-agent', agent_type=Agent.CORPORATION, canonical_name='Corp Agent'
        )

    def test_create_person_identifier(self):
        identifier = PersonIdentifier.objects.create(
            agent=self.person,
            identifier_type=PersonIdentifier.ORCID,
            value='0000-0002-1825-0097',
        )
        self.assertEqual(identifier.identifier_type, PersonIdentifier.ORCID)
        self.assertEqual(str(identifier), 'ORCID: 0000-0002-1825-0097')

    def test_reject_corporation_agent(self):
        identifier = PersonIdentifier(
            agent=self.corporation,
            identifier_type=PersonIdentifier.GND,
            value='1234567-8',
        )
        with self.assertRaises(ValidationError):
            identifier.full_clean()

    def test_unique_identifier_type_per_agent(self):
        PersonIdentifier.objects.create(
            agent=self.person,
            identifier_type=PersonIdentifier.ISNI,
            value='0000000121032683',
        )
        with self.assertRaises(ValidationError):
            duplicate = PersonIdentifier(
                agent=self.person,
                identifier_type=PersonIdentifier.ISNI,
                value='000000012146438X',
            )
            duplicate.full_clean()

    def test_unique_identifier_value_per_type(self):
        PersonIdentifier.objects.create(
            agent=self.person,
            identifier_type=PersonIdentifier.GND,
            value='118540238',
        )
        other_person = Agent.objects.create(
            slug='other-person', agent_type=Agent.PERSON, canonical_name='Other Person'
        )
        with self.assertRaises(ValidationError):
            duplicate = PersonIdentifier(
                agent=other_person,
                identifier_type=PersonIdentifier.GND,
                value='118540238',
            )
            duplicate.full_clean()


class ManifestationModelTests(TestCase):
    def setUp(self):
        self.work = Work.objects.create(slug='a-work', work_type=Work.BOOK, canonical_title='A Work')

    def test_create_manifestation(self):
        mf = Manifestation.objects.create(
            work=self.work, slug='a-work-2024', canonical_title='A Work', year=2024, publisher='Press'
        )
        self.assertEqual(mf.work, self.work)
        self.assertEqual(mf.year, 2024)

    def test_multiple_manifestations_per_work(self):
        mf1 = Manifestation.objects.create(work=self.work, slug='a-work-1st', year=2010)
        mf2 = Manifestation.objects.create(work=self.work, slug='a-work-2nd', year=2020)
        self.assertIn(mf1, self.work.manifestations.all())
        self.assertIn(mf2, self.work.manifestations.all())

    def test_str_uses_english_title(self):
        mf = Manifestation.objects.create(work=self.work, slug='mf-str', canonical_title='Fallback')
        ManifestationTitle.objects.create(manifestation=mf, language='en', label='English Title')
        self.assertEqual(str(mf), 'English Title')

    def test_str_falls_back_to_canonical_title(self):
        mf = Manifestation.objects.create(work=self.work, slug='mf-canonical', canonical_title='Canonical')
        self.assertEqual(str(mf), 'Canonical')

    def test_str_falls_back_to_slug(self):
        mf = Manifestation.objects.create(work=self.work, slug='mf-bare')
        self.assertEqual(str(mf), 'mf-bare')


class ManifestationTitleModelTests(TestCase):
    def setUp(self):
        self.work = Work.objects.create(slug='titled-mf-work', canonical_title='W')
        self.mf = Manifestation.objects.create(work=self.work, slug='titled-mf')

    def test_create_title(self):
        t = ManifestationTitle.objects.create(manifestation=self.mf, language='en', label='My Title')
        self.assertEqual(str(t), 'My Title (en)')

    def test_sort_key_optional(self):
        t = ManifestationTitle.objects.create(manifestation=self.mf, language='la', label='Titulus')
        self.assertEqual(t.sort_key, '')

    def test_unique_together(self):
        ManifestationTitle.objects.create(manifestation=self.mf, language='en', label='Dup')
        with self.assertRaises(IntegrityError):
            ManifestationTitle.objects.create(manifestation=self.mf, language='en', label='Dup')


class ContributorRoleTests(TestCase):
    def test_all_roles_defined(self):
        roles = {r.value for r in ContributorRole}
        expected = {'author', 'editor', 'advisor', 'composer', 'copy-editor', 'illustrator', 'translator'}
        self.assertEqual(roles, expected)


class WorkContributionTests(TestCase):
    def setUp(self):
        self.work = Work.objects.create(slug='contrib-work', canonical_title='Contrib Work')
        self.agent = Agent.objects.create(slug='author-agent', canonical_name='Author')

    def test_create_contribution(self):
        wc = WorkContribution.objects.create(
            id='contrib-author', work=self.work, agent=self.agent, role=ContributorRole.AUTHOR
        )
        self.assertEqual(wc.role, 'author')
        self.assertEqual(wc.pk, 'contrib-author')

    def test_unique_together(self):
        WorkContribution.objects.create(
            id='contrib-1', work=self.work, agent=self.agent, role=ContributorRole.AUTHOR
        )
        with self.assertRaises(Exception):
            WorkContribution.objects.create(
                id='contrib-2', work=self.work, agent=self.agent, role=ContributorRole.AUTHOR
            )

    def test_same_agent_different_roles_allowed(self):
        WorkContribution.objects.create(
            id='contrib-author', work=self.work, agent=self.agent, role=ContributorRole.AUTHOR
        )
        WorkContribution.objects.create(
            id='contrib-editor', work=self.work, agent=self.agent, role=ContributorRole.EDITOR
        )
        self.assertEqual(self.work.contributions.count(), 2)


class EffectiveContributionsTests(TestCase):
    def setUp(self):
        self.work = Work.objects.create(slug='eff-work', canonical_title='Eff Work')
        self.mf = Manifestation.objects.create(work=self.work, slug='eff-mf')
        self.agent_a = Agent.objects.create(slug='agent-a', canonical_name='A')
        self.agent_b = Agent.objects.create(slug='agent-b', canonical_name='B')
        self.agent_c = Agent.objects.create(slug='agent-c', canonical_name='C')

    def test_only_work_contributions(self):
        WorkContribution.objects.create(
            id='eff-work-author', work=self.work, agent=self.agent_a, role=ContributorRole.AUTHOR
        )
        effective = self.mf.effective_contributions()
        self.assertEqual(len(effective), 1)
        self.assertEqual(effective[0].agent, self.agent_a)

    def test_union_no_overlap(self):
        WorkContribution.objects.create(
            id='eff-work-author', work=self.work, agent=self.agent_a, role=ContributorRole.AUTHOR
        )
        ManifestationContribution.objects.create(
            manifestation=self.mf, agent=self.agent_b, role=ContributorRole.TRANSLATOR
        )
        effective = self.mf.effective_contributions()
        agent_ids = [c.agent_id for c in effective]
        self.assertIn(self.agent_a.pk, agent_ids)
        self.assertIn(self.agent_b.pk, agent_ids)
        self.assertEqual(len(effective), 2)

    def test_duplicate_agent_role_ignored(self):
        """If same (agent, role) exists at work and manifestation level, mf entry is ignored."""
        WorkContribution.objects.create(
            id='eff-work-author', work=self.work, agent=self.agent_a, role=ContributorRole.AUTHOR
        )
        ManifestationContribution.objects.create(
            manifestation=self.mf, agent=self.agent_a, role=ContributorRole.AUTHOR
        )
        effective = self.mf.effective_contributions()
        self.assertEqual(len(effective), 1)
        self.assertIsInstance(effective[0], WorkContribution)

    def test_same_agent_different_roles_both_included(self):
        """Same agent with different roles at work and manifestation level: both included."""
        WorkContribution.objects.create(
            id='eff-work-author', work=self.work, agent=self.agent_a, role=ContributorRole.AUTHOR
        )
        ManifestationContribution.objects.create(
            manifestation=self.mf, agent=self.agent_a, role=ContributorRole.TRANSLATOR
        )
        effective = self.mf.effective_contributions()
        roles = {c.role for c in effective}
        self.assertIn('author', roles)
        self.assertIn('translator', roles)
        self.assertEqual(len(effective), 2)


class ReferenceModelTests(TestCase):
    def setUp(self):
        self.work = Work.objects.create(slug='ref-work', work_type=Work.BOOK, canonical_title='Ref Work')
        self.mf = Manifestation.objects.create(work=self.work, slug='ref-mf', canonical_title='Ref Work')

    def test_create_reference(self):
        r = Reference.objects.create(manifestation=self.mf, page_start=1, page_end=10)
        self.assertEqual(r.manifestation, self.mf)

    def test_reference_supports_raw_metadata_fields(self):
        r = Reference.objects.create(
            manifestation=self.mf,
            raw_reference='Habermas, J.: „...“, Sp. 2',
            raw_document='Habermas, J.: „...“',
            source_file='Index B.odt',
            source_paragraph_number=202,
            page_start=2,
            page_end=2,
        )
        self.assertEqual(r.raw_document, 'Habermas, J.: „...“')
        self.assertEqual(r.source_file, 'Index B.odt')
        self.assertEqual(r.source_paragraph_number, 202)

    def test_str_single_page(self):
        r = Reference.objects.create(manifestation=self.mf, page_start=5, page_end=5)
        self.assertIn('p. 5', str(r))

    def test_str_page_range(self):
        r = Reference.objects.create(manifestation=self.mf, page_start=5, page_end=10)
        self.assertIn('pp. 5', str(r))

    def test_str_single_page_after_relation(self):
        r = Reference.objects.create(
            manifestation=self.mf,
            page_start=64,
            page_start_relation=Reference.RELATION_AFTER,
            page_end=64,
            page_end_relation=Reference.RELATION_AFTER,
        )
        self.assertIn('after p. 64', str(r))

    def test_effective_relations_default_to_on(self):
        r = Reference.objects.create(manifestation=self.mf, page_start=64, page_end=64)
        self.assertEqual(r.page_start_relation, '')
        self.assertEqual(r.page_end_relation, '')
        self.assertEqual(r.effective_page_start_relation, Reference.RELATION_ON)
        self.assertEqual(r.effective_page_end_relation, Reference.RELATION_ON)

    def test_clean_rejects_invalid_range(self):
        r = Reference(manifestation=self.mf, page_start=10, page_end=5)
        with self.assertRaises(ValidationError):
            r.clean()


class ReferenceLocatorModelTests(TestCase):
    def setUp(self):
        self.work = Work.objects.create(slug='locator-work', canonical_title='Locator Work')
        self.mf = Manifestation.objects.create(work=self.work, slug='locator-mf', canonical_title='Locator Mf')
        self.reference = Reference.objects.create(manifestation=self.mf, page_start=1, page_end=1)

    def test_defaults_are_compact(self):
        locator = ReferenceLocator.objects.create(
            reference=self.reference,
            raw_locator='64(B)',
            locator_start=64,
            locator_end=64,
        )
        self.assertEqual(locator.locator_unit, '')
        self.assertEqual(locator.start_relation, '')
        self.assertEqual(locator.end_relation, '')
        self.assertEqual(locator.locator_scope, '')
        self.assertEqual(locator.reference_type_codes, '')
        self.assertEqual(locator.effective_locator_unit, 'page')
        self.assertEqual(locator.effective_start_relation, 'on')
        self.assertEqual(locator.effective_end_relation, 'on')
        self.assertEqual(locator.effective_reference_type_codes, ('T',))

    def test_passim_rejects_numeric_values(self):
        locator = ReferenceLocator(
            reference=self.reference,
            raw_locator='passim',
            locator_scope=ReferenceLocator.SCOPE_PASSIM,
            locator_start=1,
        )
        with self.assertRaises(ValidationError):
            locator.full_clean()

    def test_relation_requires_numeric_boundary(self):
        locator = ReferenceLocator(
            reference=self.reference,
            raw_locator='nach S. 64(B)',
            start_relation=ReferenceLocator.RELATION_AFTER,
        )
        with self.assertRaises(ValidationError):
            locator.full_clean()

    def test_rejects_unsorted_or_duplicate_reference_type_codes(self):
        locator = ReferenceLocator(
            reference=self.reference,
            raw_locator='64(T+B)',
            locator_start=64,
            locator_end=64,
            reference_type_codes='BTB',
        )
        with self.assertRaises(ValidationError):
            locator.full_clean()

        locator.reference_type_codes = 'ZB'
        with self.assertRaises(ValidationError):
            locator.full_clean()

    def test_accepts_normalized_locator_metadata(self):
        locator = ReferenceLocator(
            reference=self.reference,
            order=1,
            locator_unit=ReferenceLocator.UNIT_COLUMN,
            locator_start=1,
            locator_end=2,
            raw_locator='Sp. 1/2',
            reference_type_codes='BZ',
        )
        locator.full_clean()
        self.assertEqual(str(locator), 'Sp. 1/2')


class IndexEntryCrossReferenceModelTests(TestCase):
    def setUp(self):
        self.source = IndexEntry.objects.create()
        IndexEntryLabel.objects.create(index_entry=self.source, language='de', label='Andromeda')
        self.target = IndexEntry.objects.create()
        IndexEntryLabel.objects.create(index_entry=self.target, language='de', label='Perseus und')

    def test_create_cross_reference_with_unresolved_target(self):
        ref = IndexEntryCrossReference.objects.create(
            source_entry=self.source,
            kind=IndexEntryCrossReference.KIND_SEE,
            marker='s.',
            target_raw='Andromeda; Perseus und',
        )
        self.assertIsNone(ref.target_entry)
        self.assertEqual(ref.kind, IndexEntryCrossReference.KIND_SEE)

    def test_create_cross_reference_with_resolved_target(self):
        ref = IndexEntryCrossReference.objects.create(
            source_entry=self.source,
            target_entry=self.target,
            kind=IndexEntryCrossReference.KIND_SEE_ALSO,
            marker='siehe auch',
            target_raw='Andromeda; Perseus und',
            order=2,
        )
        self.assertEqual(ref.target_entry, self.target)
        self.assertEqual(ref.order, 2)


class ReferenceFixtureExportTests(TestCase):
    def test_build_reference_fixture_rows_from_parsed_payload(self):
        from .reference_fixtures import build_reference_fixture_rows

        payload = {
            'documents': {
                '0': {'label': 'Fassmann, K. (Hg.): „Die Großen“, Bd. X', 'normalized_label': 'fassmann k hg die grossen bd x'},
                '1': {
                    'label': 'Arnoldi, E. F.: „Marc Chagall“',
                    'normalized_label': 'arnoldi e f marc chagall',
                    'part_of': '0',
                },
            },
            'entries': [
                {
                    'source_file': 'Index A.odt',
                    'paragraph_number': 7,
                    'raw_lemma': 'Müller, Anna',
                    'references': [
                        {
                            'kind': 'page',
                            'document': '1',
                            'page_locators': [
                                {
                                    'raw': 'S. 64(B)',
                                    'page_start': 64,
                                    'page_end': 64,
                                    'page_start_relation': '',
                                    'page_end_relation': '',
                                    'note': '(B)',
                                    'reference_types': ['B'],
                                    'locator_unit': 'page',
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        rows = build_reference_fixture_rows(payload, manifestation_id=42)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['model'], 'indexer.reference')
        self.assertEqual(rows[0]['fields']['manifestation'], 42)
        self.assertEqual(rows[0]['fields']['raw_document'], 'Arnoldi, E. F.: „Marc Chagall“')
        self.assertEqual(rows[0]['fields']['raw_document_part_of'], 'Fassmann, K. (Hg.): „Die Großen“, Bd. X')
        self.assertEqual(rows[1]['model'], 'indexer.referencelocator')
        self.assertEqual(rows[1]['fields']['reference'], rows[0]['pk'])
        self.assertEqual(rows[1]['fields']['locator_start'], 64)

    def test_build_reference_fixture_rows_omits_oversized_raw_reference_and_truncates_document_text(self):
        from .reference_fixtures import build_reference_fixture_rows

        payload = {
            'documents': {
                '0': {'label': 'Container ' + ('x' * 2000), 'normalized_label': 'container'},
                '1': {'label': 'Leaf ' + ('y' * 2000), 'normalized_label': 'leaf', 'part_of': '0'},
            },
            'entries': [
                {
                    'source_file': 'Index A.odt',
                    'paragraph_number': 9,
                    'raw_lemma': 'Test lemma',
                    'references': [
                        {
                            'kind': 'page',
                            'document': '1',
                            'page_locators': [
                                {
                                    'raw': 'S. ' + ('9' * 2000),
                                    'page_start': 9,
                                    'page_end': 9,
                                    'page_start_relation': '',
                                    'page_end_relation': '',
                                    'note': '',
                                    'reference_types': ['T'],
                                    'locator_unit': 'page',
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        rows = build_reference_fixture_rows(payload, manifestation_id=42)
        reference_fields = rows[0]['fields']
        self.assertNotIn('raw_reference', reference_fields)
        self.assertLessEqual(len(reference_fields['raw_document']), 1000)
        self.assertLessEqual(len(reference_fields['raw_document_part_of']), 1000)


class ManifestationSuggestionModelTests(TestCase):
    def setUp(self):
        self.work = Work.objects.create(
            slug='suggestion-work', work_type=Work.BOOK, canonical_title='Suggestion Work'
        )
        self.matching_manifestation = Manifestation.objects.create(
            work=self.work,
            slug='matching-manifestation',
            canonical_title='Die Belagerung zu Peking. Zur Geschichte des Boxer-Aufstandes',
            year=1997,
            publisher='Eichborn',
            isbn_issn='3-8218-4155-9',
        )
        self.unrelated_manifestation = Manifestation.objects.create(
            work=self.work,
            slug='unrelated-manifestation',
            canonical_title='Something Else Entirely',
            year=2001,
            publisher='Other',
        )
        self.reference = Reference.objects.create(
            manifestation=self.matching_manifestation,
            raw_document='Die Belagerung zu Peking. Zur Geschichte des Boxer-Aufstandes',
            raw_reference='Die Belagerung zu Peking. Zur Geschichte des Boxer-Aufstandes',
            page_start=1,
            page_end=1,
        )

    def test_normalize_title_removes_punctuation_and_case(self):
        normalized = normalize_title('Die Belagerung zu Peking. Zur Geschichte des Boxer-Aufstandes')
        self.assertEqual(normalized, 'belagerung peking geschichte boxer aufstandes')

    def test_suggest_manifestation_matches_title(self):
        suggestions = suggest_manifestation_matches(
            self.reference,
            Manifestation.objects.filter(pk__in=[self.matching_manifestation.pk, self.unrelated_manifestation.pk]),
            max_candidates=5,
            min_score=60,
        )
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].manifestation, self.matching_manifestation)
        self.assertGreaterEqual(suggestions[0].score, 80)
        self.assertEqual(suggestions[0].match_type, 'title')

    def test_suggest_manifestation_matches_uses_parent_document_context(self):
        parent_reference = Reference.objects.create(
            manifestation=self.matching_manifestation,
            raw_document='Marc Chagall',
            raw_document_part_of='Die Großen',
            raw_reference='Marc Chagall',
            page_start=1,
            page_end=1,
        )
        self.matching_manifestation.canonical_title = 'Die Großen'
        self.matching_manifestation.save(update_fields=['canonical_title'])

        suggestions = suggest_manifestation_matches(
            parent_reference,
            Manifestation.objects.filter(pk=self.matching_manifestation.pk),
            max_candidates=5,
            min_score=40,
        )

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].manifestation, self.matching_manifestation)
        self.assertIn('container_similarity', suggestions[0].details)

    def test_create_suggestion_row(self):
        suggestion = ManifestationSuggestion.objects.create(
            reference=self.reference,
            manifestation=self.matching_manifestation,
            score=92,
            match_type='title',
            status='suggested',
            details={'matched_title': 'Die Belagerung zu Peking. Zur Geschichte des Boxer-Aufstandes'},
        )
        self.assertEqual(suggestion.score, 92)
        self.assertEqual(suggestion.match_type, 'title')
        self.assertEqual(suggestion.status, 'suggested')


