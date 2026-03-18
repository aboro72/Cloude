from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupshare',
            name='background_image',
            field=models.ImageField(blank=True, null=True, upload_to='groups/backgrounds/%Y/%m/', verbose_name='Background image'),
        ),
    ]
