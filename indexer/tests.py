from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import (
    IndexEntry,
    IndexEntryLabel,
    IndexEntryReference,
    Reference,
    Work,
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
        with self.assertRaises(Exception):
            WorkTitle.objects.create(work=self.work, language='en', label='Dup')

    def test_sort_key_optional(self):
        t = WorkTitle.objects.create(work=self.work, language='la', label='Opus')
        self.assertEqual(t.sort_key, '')


class ReferenceModelTests(TestCase):
    def setUp(self):
        self.work = Work.objects.create(slug='ref-work', work_type=Work.BOOK, canonical_title='Ref Work')

    def test_create_reference(self):
        r = Reference.objects.create(work=self.work, page_start=1, page_end=10)
        self.assertEqual(r.work, self.work)

    def test_str_single_page(self):
        r = Reference.objects.create(work=self.work, page_start=5, page_end=5)
        self.assertIn('p. 5', str(r))

    def test_str_page_range(self):
        r = Reference.objects.create(work=self.work, page_start=5, page_end=10)
        self.assertIn('pp. 5', str(r))

    def test_clean_rejects_invalid_range(self):
        r = Reference(work=self.work, page_start=10, page_end=5)
        with self.assertRaises(ValidationError):
            r.clean()

    def test_reference_to_chapter(self):
        book = Work.objects.create(slug='a-book', work_type=Work.BOOK)
        chapter = Work.objects.create(slug='a-chapter', work_type=Work.CHAPTER, parent=book)
        r = Reference.objects.create(work=chapter, page_start=1, page_end=2)
        self.assertEqual(r.work.work_type, Work.CHAPTER)

