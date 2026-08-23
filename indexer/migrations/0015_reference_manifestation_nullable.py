from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('indexer', '0014_reference_raw_document_part_of'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reference',
            name='manifestation',
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='references',
                to='indexer.manifestation',
            ),
        ),
    ]
