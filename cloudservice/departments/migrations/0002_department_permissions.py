from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('departments', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='department',
            options={
                'ordering': ['name'],
                'permissions': [
                    ('create_department', 'Kann Abteilungen erstellen'),
                    ('manage_any_department', 'Kann beliebige Abteilungen verwalten'),
                ],
                'verbose_name': 'Abteilung',
                'verbose_name_plural': 'Abteilungen',
            },
        ),
    ]
