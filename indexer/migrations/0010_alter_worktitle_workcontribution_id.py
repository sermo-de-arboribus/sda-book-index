from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('indexer', '0009_personidentifier'),
    ]

    operations = [
        migrations.AlterField(
            model_name='worktitle',
            name='id',
            field=models.CharField(max_length=255, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='workcontribution',
            name='id',
            field=models.CharField(max_length=255, primary_key=True, serialize=False),
        ),
    ]