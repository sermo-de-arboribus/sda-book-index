from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from .models import (
    Agent,
    AgentName,
    ContributorRole,
    IndexEntry,
    IndexEntryLabel,
    IndexEntryReference,
    Manifestation,
    ManifestationContribution,
    ManifestationTitle,
    Reference,
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
        WorkTitle.objects.create(work=w, language='de', label='Deutsches Buch')
        WorkTitle.objects.create(work=w, language='en', label='English Book')
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
        t = WorkTitle.objects.create(work=self.work, language='en', label='Titled Work')
        self.assertEqual(str(t), 'Titled Work (en)')

    def test_unique_together(self):
        WorkTitle.objects.create(work=self.work, language='en', label='Dup')
        with self.assertRaises(IntegrityError):
            WorkTitle.objects.create(work=self.work, language='en', label='Dup')

    def test_sort_key_optional(self):
        t = WorkTitle.objects.create(work=self.work, language='la', label='Opus')
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
            work=self.work, agent=self.agent, role=ContributorRole.AUTHOR
        )
        self.assertEqual(wc.role, 'author')

    def test_unique_together(self):
        WorkContribution.objects.create(work=self.work, agent=self.agent, role=ContributorRole.AUTHOR)
        with self.assertRaises(Exception):
            WorkContribution.objects.create(work=self.work, agent=self.agent, role=ContributorRole.AUTHOR)

    def test_same_agent_different_roles_allowed(self):
        WorkContribution.objects.create(work=self.work, agent=self.agent, role=ContributorRole.AUTHOR)
        WorkContribution.objects.create(work=self.work, agent=self.agent, role=ContributorRole.EDITOR)
        self.assertEqual(self.work.contributions.count(), 2)


class EffectiveContributionsTests(TestCase):
    def setUp(self):
        self.work = Work.objects.create(slug='eff-work', canonical_title='Eff Work')
        self.mf = Manifestation.objects.create(work=self.work, slug='eff-mf')
        self.agent_a = Agent.objects.create(slug='agent-a', canonical_name='A')
        self.agent_b = Agent.objects.create(slug='agent-b', canonical_name='B')
        self.agent_c = Agent.objects.create(slug='agent-c', canonical_name='C')

    def test_only_work_contributions(self):
        WorkContribution.objects.create(work=self.work, agent=self.agent_a, role=ContributorRole.AUTHOR)
        effective = self.mf.effective_contributions()
        self.assertEqual(len(effective), 1)
        self.assertEqual(effective[0].agent, self.agent_a)

    def test_union_no_overlap(self):
        WorkContribution.objects.create(work=self.work, agent=self.agent_a, role=ContributorRole.AUTHOR)
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
        WorkContribution.objects.create(work=self.work, agent=self.agent_a, role=ContributorRole.AUTHOR)
        ManifestationContribution.objects.create(
            manifestation=self.mf, agent=self.agent_a, role=ContributorRole.AUTHOR
        )
        effective = self.mf.effective_contributions()
        self.assertEqual(len(effective), 1)
        self.assertIsInstance(effective[0], WorkContribution)

    def test_same_agent_different_roles_both_included(self):
        """Same agent with different roles at work and manifestation level: both included."""
        WorkContribution.objects.create(work=self.work, agent=self.agent_a, role=ContributorRole.AUTHOR)
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

    def test_str_single_page(self):
        r = Reference.objects.create(manifestation=self.mf, page_start=5, page_end=5)
        self.assertIn('p. 5', str(r))

    def test_str_page_range(self):
        r = Reference.objects.create(manifestation=self.mf, page_start=5, page_end=10)
        self.assertIn('pp. 5', str(r))

    def test_clean_rejects_invalid_range(self):
        r = Reference(manifestation=self.mf, page_start=10, page_end=5)
        with self.assertRaises(ValidationError):
            r.clean()


