from django.core.validators import RegexValidator
from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='color_preset',
            field=models.CharField(
                choices=[
                    ('default', 'Default Blue'),
                    ('forest', 'Forest'),
                    ('sunset', 'Sunset'),
                    ('berry', 'Berry'),
                    ('slate', 'Slate'),
                    ('custom', 'Custom'),
                ],
                default='default',
                max_length=20,
                verbose_name='Color preset',
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='design_variant',
            field=models.CharField(
                choices=[('gradient', 'Gradient'), ('minimal', 'Minimal'), ('contrast', 'Contrast')],
                default='gradient',
                max_length=20,
                verbose_name='Design variant',
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='primary_color',
            field=models.CharField(
                default='#667eea',
                max_length=7,
                validators=[
                    RegexValidator(
                        message=_('Use a valid hex color like #667EEA.'),
                        regex='^#[0-9A-Fa-f]{6}$',
                    )
                ],
                verbose_name='Primary color',
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='secondary_color',
            field=models.CharField(
                default='#764ba2',
                max_length=7,
                validators=[
                    RegexValidator(
                        message=_('Use a valid hex color like #667EEA.'),
                        regex='^#[0-9A-Fa-f]{6}$',
                    )
                ],
                verbose_name='Secondary color',
            ),
        ),
    ]
