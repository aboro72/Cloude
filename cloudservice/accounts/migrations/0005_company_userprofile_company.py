# Generated manually for company workspace support.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_people_directory_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=180, unique=True, verbose_name='Company name')),
                ('slug', models.SlugField(max_length=180, unique=True, verbose_name='Company slug')),
                (
                    'workspace_type',
                    models.CharField(
                        choices=[('directory', 'Directory'), ('subdomain', 'Subdomain')],
                        default='directory',
                        max_length=20,
                        verbose_name='Workspace type',
                    ),
                ),
                (
                    'workspace_key',
                    models.SlugField(
                        help_text='Used for the company directory or subdomain.',
                        max_length=63,
                        unique=True,
                        verbose_name='Workspace key',
                    ),
                ),
                ('included_free_employees', models.PositiveSmallIntegerField(default=5, verbose_name='Included free employees')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
            ],
            options={
                'verbose_name': 'Company',
                'verbose_name_plural': 'Companies',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='userprofile',
            name='company',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='members',
                to='accounts.company',
                verbose_name='Company',
            ),
        ),
    ]
