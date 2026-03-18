# Add 'uninstalled' to PluginLog.action choices.
# CharField choices are enforced in Python only, so no schema change is needed,
# but Django requires a migration to keep the recorded state in sync.

from django.db import migrations, models
import django.utils.translation


class Migration(migrations.Migration):

    dependencies = [
        ('plugins', '0004_add_plugin_settings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pluginlog',
            name='action',
            field=models.CharField(
                choices=[
                    ('uploaded', django.utils.translation.gettext_lazy('Uploaded')),
                    ('activated', django.utils.translation.gettext_lazy('Activated')),
                    ('deactivated', django.utils.translation.gettext_lazy('Deactivated')),
                    ('uninstalled', django.utils.translation.gettext_lazy('Uninstalled')),
                    ('error', django.utils.translation.gettext_lazy('Error')),
                ],
                db_index=True,
                help_text='Type of action performed',
                max_length=20,
            ),
        ),
    ]
