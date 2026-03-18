from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing', '0002_groupshare_background_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupshare',
            name='background_video',
            field=models.FileField(blank=True, null=True, upload_to='groups/backgrounds/%Y/%m/', verbose_name='Background video'),
        ),
    ]
