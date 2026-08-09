from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('indexer', '0010_alter_worktitle_workcontribution_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='reference',
            name='page_end_relation',
            field=models.CharField(blank=True, choices=[('', 'on'), ('before', 'before'), ('after', 'after')], default='', max_length=6),
        ),
        migrations.AddField(
            model_name='reference',
            name='page_start_relation',
            field=models.CharField(blank=True, choices=[('', 'on'), ('before', 'before'), ('after', 'after')], default='', max_length=6),
        ),
    ]