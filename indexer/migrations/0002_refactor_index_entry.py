import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indexer', '0001_initial'),
    ]

    operations = [
        # Remove the person and subject FKs from IndexEntry
        migrations.RemoveField(
            model_name='indexentry',
            name='person',
        ),
        migrations.RemoveField(
            model_name='indexentry',
            name='subject',
        ),
        # Fix the ordering that referenced the now-removed fields
        migrations.AlterModelOptions(
            name='indexentry',
            options={'verbose_name_plural': 'index entries'},
        ),
        # Add self-referential parent FK
        migrations.AddField(
            model_name='indexentry',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='children',
                to='indexer.indexentry',
                db_index=True,
            ),
        ),
        # Create the IndexEntryLabel model
        migrations.CreateModel(
            name='IndexEntryLabel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(db_index=True, max_length=35)),
                ('label', models.CharField(max_length=500)),
                ('sort_key', models.CharField(blank=True, max_length=500)),
                ('index_entry', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='labels',
                    to='indexer.indexentry',
                )),
            ],
            options={
                'ordering': ['language'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='indexentrylabel',
            unique_together={('index_entry', 'language', 'label')},
        ),
        migrations.AddIndex(
            model_name='indexentrylabel',
            index=models.Index(fields=['index_entry', 'language'], name='indexer_ind_index_e_cf5d63_idx'),
        ),
        migrations.AddIndex(
            model_name='indexentrylabel',
            index=models.Index(fields=['language', 'label'], name='indexer_ind_languag_2a212e_idx'),
        ),
    ]
