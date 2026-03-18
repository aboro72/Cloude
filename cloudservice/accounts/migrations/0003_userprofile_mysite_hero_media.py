from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_userprofile_appearance_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='mysite_hero_image',
            field=models.ImageField(blank=True, null=True, upload_to='mysite/hero/%Y/%m/', verbose_name='MySite hero image'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='mysite_hero_style',
            field=models.CharField(
                choices=[('gradient', 'Gradient'), ('image', 'Image'), ('video', 'Video')],
                default='gradient',
                max_length=20,
                verbose_name='MySite hero style',
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='mysite_hero_video',
            field=models.FileField(blank=True, null=True, upload_to='mysite/hero/%Y/%m/', verbose_name='MySite hero video'),
        ),
    ]
