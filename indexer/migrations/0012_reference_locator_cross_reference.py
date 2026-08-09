from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('indexer', '0011_reference_page_relations'),
    ]

    operations = [
        migrations.AddField(
            model_name='reference',
            name='raw_document',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AddField(
            model_name='reference',
            name='raw_reference',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='reference',
            name='source_file',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='reference',
            name='source_paragraph_number',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='reference',
            index=models.Index(fields=['manifestation', 'raw_document'], name='indexer_ref_mf_doc_idx'),
        ),
        migrations.CreateModel(
            name='ReferenceLocator',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(db_index=True, default=0)),
                ('locator_unit', models.CharField(blank=True, choices=[('', 'page'), ('column', 'column'), ('figure', 'figure')], default='', max_length=10)),
                ('locator_start', models.PositiveIntegerField(blank=True, null=True)),
                ('locator_end', models.PositiveIntegerField(blank=True, null=True)),
                ('start_relation', models.CharField(blank=True, choices=[('', 'on'), ('before', 'before'), ('after', 'after')], default='', max_length=6)),
                ('end_relation', models.CharField(blank=True, choices=[('', 'on'), ('before', 'before'), ('after', 'after')], default='', max_length=6)),
                ('locator_scope', models.CharField(blank=True, choices=[('', 'normal'), ('passim', 'passim')], default='', max_length=12)),
                ('raw_locator', models.CharField(max_length=255)),
                ('reference_type_codes', models.CharField(blank=True, default='', max_length=16)),
                ('reference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='locators', to='indexer.reference')),
            ],
            options={
                'ordering': ['order', 'locator_start', 'locator_end'],
                'indexes': [
                    models.Index(fields=['reference', 'order'], name='indexer_rl_ref_order_idx'),
                    models.Index(fields=['locator_unit', 'locator_start'], name='indexer_rl_unit_start_idx'),
                    models.Index(fields=['locator_scope'], name='indexer_rl_scope_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='IndexEntryCrossReference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('see', 'See'), ('see_also', 'See also'), ('compare', 'Compare')], max_length=12)),
                ('marker', models.CharField(max_length=20)),
                ('target_raw', models.CharField(max_length=1000)),
                ('order', models.PositiveIntegerField(db_index=True, default=0)),
                ('source_entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cross_references', to='indexer.indexentry')),
                ('target_entry', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='incoming_cross_references', to='indexer.indexentry')),
            ],
            options={
                'ordering': ['order', 'kind', 'target_raw'],
                'indexes': [
                    models.Index(fields=['source_entry', 'order'], name='indexer_ixcr_src_order_idx'),
                    models.Index(fields=['target_entry'], name='indexer_ixcr_target_idx'),
                    models.Index(fields=['kind'], name='indexer_ixcr_kind_idx'),
                ],
            },
        ),
    ]