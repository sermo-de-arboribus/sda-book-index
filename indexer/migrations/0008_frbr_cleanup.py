import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Finalize FRBR schema: make Reference.manifestation non-nullable,
    drop old Reference.work FK, drop Work.year/publisher/isbn_issn,
    and remove Person/PersonName."""

    dependencies = [
        ('indexer', '0007_frbr_data_migration'),
    ]

    operations = [
        # --- Update IndexEntryReference ordering to use manifestation ---
        migrations.AlterModelOptions(
            name='indexentryreference',
            options={'ordering': ['order', 'reference__manifestation__slug', 'reference__page_start']},
        ),

        # --- Make Reference.manifestation non-nullable ---
        migrations.AlterField(
            model_name='reference',
            name='manifestation',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='references', to='indexer.manifestation',
            ),
        ),

        # --- Update Reference ordering and add index ---
        migrations.AlterModelOptions(
            name='reference',
            options={'ordering': ['manifestation', 'page_start', 'page_end']},
        ),
        migrations.AddIndex(
            model_name='reference',
            index=models.Index(fields=['manifestation', 'page_start'], name='indexer_ref_mf_start_idx'),
        ),

        # --- Remove Reference.work FK and its index ---
        migrations.RemoveIndex(
            model_name='reference',
            name='indexer_ref_work_start_idx',
        ),
        migrations.RemoveField(
            model_name='reference',
            name='work',
        ),

        # --- Remove Work.year, Work.publisher, Work.isbn_issn ---
        migrations.RemoveField(model_name='work', name='year'),
        migrations.RemoveField(model_name='work', name='publisher'),
        migrations.RemoveField(model_name='work', name='isbn_issn'),

        # --- Remove PersonName then Person ---
        migrations.AlterUniqueTogether(
            name='personname',
            unique_together=None,
        ),
        migrations.RemoveField(model_name='personname', name='person'),
        migrations.DeleteModel(name='PersonName'),
        migrations.DeleteModel(name='Person'),
    ]
