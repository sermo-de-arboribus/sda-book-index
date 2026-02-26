import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indexer', '0004_book_to_work_data_migration'),
    ]

    operations = [
        # Update ordering metadata (no schema changes)
        migrations.AlterModelOptions(
            name='indexentryreference',
            options={'ordering': ['order', 'reference__work__slug', 'reference__page_start']},
        ),
        migrations.AlterModelOptions(
            name='reference',
            options={'ordering': ['work', 'page_start', 'page_end']},
        ),
        # Remove old book-based index on Reference before switching the field
        migrations.RemoveIndex(
            model_name='reference',
            name='indexer_ref_book_id_eefbaf_idx',
        ),
        # Make Reference.work non-nullable now that the data migration has run
        migrations.AlterField(
            model_name='reference',
            name='work',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='references', to='indexer.work'),
        ),
        # Add work-based index on Reference
        migrations.AddIndex(
            model_name='reference',
            index=models.Index(fields=['work', 'page_start'], name='indexer_ref_work_start_idx'),
        ),
        # Drop BookTitle unique constraint before removing its FK field
        migrations.AlterUniqueTogether(
            name='booktitle',
            unique_together=None,
        ),
        # Remove BookTitle.book FK then delete the model
        migrations.RemoveField(
            model_name='booktitle',
            name='book',
        ),
        migrations.DeleteModel(
            name='BookTitle',
        ),
        # Remove Reference.book FK then delete Book
        migrations.RemoveField(
            model_name='reference',
            name='book',
        ),
        migrations.DeleteModel(
            name='Book',
        ),
    ]
