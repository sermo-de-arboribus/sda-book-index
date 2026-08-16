from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indexer', '0013_manifestationsuggestion'),
    ]

    operations = [
        migrations.AddField(
            model_name='reference',
            name='raw_document_part_of',
            field=models.CharField(blank=True, max_length=1000),
        ),
    ]
