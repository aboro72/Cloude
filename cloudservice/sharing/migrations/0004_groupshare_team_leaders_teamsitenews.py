from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing', '0003_groupshare_background_video'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='groupshare',
            name='team_leaders',
            field=models.ManyToManyField(blank=True, related_name='group_shares_led', to=settings.AUTH_USER_MODEL, verbose_name='Team leaders'),
        ),
        migrations.CreateModel(
            name='TeamSiteNews',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('summary', models.TextField(blank=True, verbose_name='Summary')),
                ('content', models.TextField(blank=True, verbose_name='Content')),
                ('cover_image', models.ImageField(blank=True, null=True, upload_to='groups/news/%Y/%m/', verbose_name='Cover image')),
                ('is_published', models.BooleanField(default=True, verbose_name='Is published')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('author', models.ForeignKey(null=True, on_delete=models.deletion.SET_NULL, related_name='team_site_news_authored', to=settings.AUTH_USER_MODEL, verbose_name='Author')),
                ('group', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='news_items', to='sharing.groupshare', verbose_name='Group')),
            ],
            options={
                'verbose_name': 'Team Site News',
                'verbose_name_plural': 'Team Site News',
                'ordering': ['-created_at'],
            },
        ),
    ]
