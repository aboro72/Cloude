# Generated manually to make NewsArticle.slug MySQL-safe.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='newsarticle',
            name='slug',
            field=models.SlugField(max_length=191, unique=True, verbose_name='Slug'),
        ),
    ]
