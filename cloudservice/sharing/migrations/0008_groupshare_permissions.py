from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sharing', '0007_groupshare_department'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='groupshare',
            options={
                'ordering': ['-created_at'],
                'permissions': [
                    ('create_groupshare', 'Kann Team-Sites erstellen'),
                    ('manage_any_groupshare', 'Kann beliebige Team-Sites verwalten'),
                ],
                'verbose_name': 'Group Share',
                'verbose_name_plural': 'Group Shares',
            },
        ),
    ]
