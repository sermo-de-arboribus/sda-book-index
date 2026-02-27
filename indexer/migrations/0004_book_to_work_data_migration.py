from django.db import migrations


def book_to_work(apps, schema_editor):
    """Create Work/WorkTitle rows from Book/BookTitle and backfill Reference.work."""
    Book = apps.get_model('indexer', 'Book')
    BookTitle = apps.get_model('indexer', 'BookTitle')
    Work = apps.get_model('indexer', 'Work')
    WorkTitle = apps.get_model('indexer', 'WorkTitle')
    Reference = apps.get_model('indexer', 'Reference')

    book_to_work_map = {}

    for book in Book.objects.all():
        # Use the first English title (or any title) as canonical_title fallback
        en_title = BookTitle.objects.filter(book=book, language='en').first()
        any_title = en_title or BookTitle.objects.filter(book=book).first()
        canonical = any_title.label if any_title else book.slug

        work = Work.objects.create(
            work_type='book',
            slug=book.slug,
            canonical_title=canonical,
        )
        book_to_work_map[book.pk] = work

        for bt in BookTitle.objects.filter(book=book):
            WorkTitle.objects.create(
                work=work,
                language=bt.language,
                label=bt.label,
            )

    for ref in Reference.objects.filter(work__isnull=True):
        ref.work = book_to_work_map.get(ref.book_id)
        ref.save()


def work_to_book(apps, schema_editor):
    """Reverse: remove Work/WorkTitle rows that were migrated from Book/BookTitle."""
    Work = apps.get_model('indexer', 'Work')
    Reference = apps.get_model('indexer', 'Reference')

    # Clear work FK from references that point to migrated works
    Reference.objects.filter(work__isnull=False).update(work=None)
    # Remove all works (only migrated ones exist at this point)
    Work.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('indexer', '0003_work_reference_work_worktitle'),
    ]

    operations = [
        migrations.RunPython(book_to_work, reverse_code=work_to_book),
    ]
