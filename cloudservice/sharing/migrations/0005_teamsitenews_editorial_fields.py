from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing', '0004_groupshare_team_leaders_teamsitenews'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamsitenews',
            name='category',
            field=models.CharField(blank=True, max_length=120, verbose_name='Category'),
        ),
        migrations.AddField(
            model_name='teamsitenews',
            name='is_pinned',
            field=models.BooleanField(default=False, verbose_name='Is pinned'),
        ),
        migrations.AddField(
            model_name='teamsitenews',
            name='publish_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Publish at'),
        ),
        migrations.AlterModelOptions(
            name='teamsitenews',
            options={'ordering': ['-is_pinned', '-publish_at', '-created_at'], 'verbose_name': 'Team Site News', 'verbose_name_plural': 'Team Site News'},
        ),
    ]
