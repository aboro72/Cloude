import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_company_userprofile_company'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='landing_title',
            field=models.CharField(
                blank=True,
                max_length=200,
                verbose_name='Landing page title',
                help_text='Leave blank to use company name.',
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='landing_subtitle',
            field=models.CharField(blank=True, max_length=400, verbose_name='Landing page subtitle'),
        ),
        migrations.AddField(
            model_name='company',
            name='landing_logo',
            field=models.ImageField(blank=True, null=True, upload_to='companies/logos/', verbose_name='Company logo'),
        ),
        migrations.AddField(
            model_name='company',
            name='landing_hero_style',
            field=models.CharField(
                choices=[('gradient', 'Gradient'), ('image', 'Image'), ('video', 'Video')],
                default='gradient',
                max_length=20,
                verbose_name='Hero style',
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='landing_hero_image',
            field=models.ImageField(
                blank=True, null=True, upload_to='companies/hero/', verbose_name='Hero background image'
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='landing_hero_video',
            field=models.FileField(
                blank=True, null=True, upload_to='companies/hero/', verbose_name='Hero background video'
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='landing_primary_color',
            field=models.CharField(
                default='#667eea',
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        regex='^#[0-9A-Fa-f]{6}$', message='Use a valid hex color like #667EEA.'
                    )
                ],
                verbose_name='Primary brand color',
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='landing_secondary_color',
            field=models.CharField(
                default='#764ba2',
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        regex='^#[0-9A-Fa-f]{6}$', message='Use a valid hex color like #667EEA.'
                    )
                ],
                verbose_name='Secondary brand color',
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='landing_custom_html',
            field=models.TextField(
                blank=True,
                verbose_name='Custom HTML block',
                help_text='Additional HTML shown on the landing page.',
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='landing_custom_css',
            field=models.TextField(blank=True, verbose_name='Custom CSS', help_text='Custom CSS applied on the landing page.'),
        ),
    ]
