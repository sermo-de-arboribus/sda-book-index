from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indexer', '0015_reference_manifestation_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='indexentry',
            name='index_type',
            field=models.CharField(
                blank=True,
                choices=[('P', 'Person index'), ('S', 'Subject index')],
                db_index=True,
                max_length=1,
                null=True,
            ),
        ),
    ]