import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Add FRBR-inspired tables: Agent, AgentName, Manifestation, ManifestationTitle,
    WorkContribution, ManifestationContribution; add nullable Reference.manifestation FK."""

    dependencies = [
        ('indexer', '0005_remove_booktitle_book_and_more'),
    ]

    operations = [
        # --- Agent ---
        migrations.CreateModel(
            name='Agent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('agent_type', models.CharField(
                    choices=[('person', 'Person'), ('corporation', 'Corporation')],
                    db_index=True, default='person', max_length=20,
                )),
                ('canonical_name', models.CharField(blank=True, max_length=500)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['slug']},
        ),
        migrations.CreateModel(
            name='AgentName',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(db_index=True, max_length=35)),
                ('label', models.CharField(max_length=500)),
                ('sort_key', models.CharField(blank=True, max_length=500)),
                ('agent', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='names', to='indexer.agent',
                )),
            ],
            options={'ordering': ['language']},
        ),
        migrations.AlterUniqueTogether(
            name='agentname',
            unique_together={('agent', 'language', 'label')},
        ),
        migrations.AddIndex(
            model_name='agentname',
            index=models.Index(fields=['agent', 'language'], name='indexer_an_agent_lang_idx'),
        ),
        migrations.AddIndex(
            model_name='agentname',
            index=models.Index(fields=['language', 'label'], name='indexer_an_lang_label_idx'),
        ),

        # --- WorkContribution ---
        migrations.CreateModel(
            name='WorkContribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[
                        ('author', 'Author'), ('editor', 'Editor'), ('advisor', 'Advisor'),
                        ('composer', 'Composer'), ('copy-editor', 'Copy-editor'),
                        ('illustrator', 'Illustrator'), ('translator', 'Translator'),
                    ],
                    max_length=20,
                )),
                ('sort_order', models.PositiveIntegerField(db_index=True, default=0)),
                ('agent', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='work_contributions', to='indexer.agent',
                )),
                ('work', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='contributions', to='indexer.work',
                )),
            ],
            options={'ordering': ['sort_order', 'agent__slug']},
        ),
        migrations.AlterUniqueTogether(
            name='workcontribution',
            unique_together={('work', 'agent', 'role')},
        ),

        # --- Manifestation ---
        migrations.CreateModel(
            name='Manifestation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('canonical_title', models.CharField(blank=True, max_length=500)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('year', models.PositiveSmallIntegerField(blank=True, db_index=True, null=True)),
                ('publisher', models.CharField(blank=True, max_length=500)),
                ('isbn_issn', models.CharField(blank=True, max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('work', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='manifestations', to='indexer.work',
                )),
            ],
            options={'ordering': ['slug']},
        ),

        # --- ManifestationTitle ---
        migrations.CreateModel(
            name='ManifestationTitle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(db_index=True, max_length=35)),
                ('label', models.CharField(max_length=500)),
                ('sort_key', models.CharField(blank=True, max_length=500)),
                ('manifestation', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='titles', to='indexer.manifestation',
                )),
            ],
            options={'ordering': ['language']},
        ),
        migrations.AlterUniqueTogether(
            name='manifestationtitle',
            unique_together={('manifestation', 'language', 'label')},
        ),
        migrations.AddIndex(
            model_name='manifestationtitle',
            index=models.Index(fields=['manifestation', 'language'], name='indexer_mt_mf_lang_idx'),
        ),
        migrations.AddIndex(
            model_name='manifestationtitle',
            index=models.Index(fields=['language', 'label'], name='indexer_mt_lang_label_idx'),
        ),

        # --- ManifestationContribution ---
        migrations.CreateModel(
            name='ManifestationContribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[
                        ('author', 'Author'), ('editor', 'Editor'), ('advisor', 'Advisor'),
                        ('composer', 'Composer'), ('copy-editor', 'Copy-editor'),
                        ('illustrator', 'Illustrator'), ('translator', 'Translator'),
                    ],
                    max_length=20,
                )),
                ('sort_order', models.PositiveIntegerField(db_index=True, default=0)),
                ('agent', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='manifestation_contributions', to='indexer.agent',
                )),
                ('manifestation', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='contributions', to='indexer.manifestation',
                )),
            ],
            options={'ordering': ['sort_order', 'agent__slug']},
        ),
        migrations.AlterUniqueTogether(
            name='manifestationcontribution',
            unique_together={('manifestation', 'agent', 'role')},
        ),

        # --- Add nullable Reference.manifestation FK ---
        migrations.AddField(
            model_name='reference',
            name='manifestation',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='references', to='indexer.manifestation',
            ),
        ),
    ]
