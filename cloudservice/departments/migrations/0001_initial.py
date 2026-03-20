from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True, verbose_name='Name')),
                ('slug', models.SlugField(blank=True, max_length=180, unique=True)),
                ('description', models.TextField(blank=True, verbose_name='Beschreibung')),
                ('icon', models.CharField(default='bi-building', max_length=60, verbose_name='Icon (Bootstrap)')),
                ('color', models.CharField(default='#667eea', max_length=7, verbose_name='Farbe (Hex)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_departments',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('head', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='headed_departments',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Abteilungsleiter',
                )),
            ],
            options={
                'verbose_name': 'Abteilung',
                'verbose_name_plural': 'Abteilungen',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='DepartmentMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[('member', 'Mitglied'), ('manager', 'Manager'), ('head', 'Abteilungsleiter')],
                    default='member',
                    max_length=20,
                )),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('department', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='memberships',
                    to='departments.department',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='department_memberships',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Mitgliedschaft',
                'verbose_name_plural': 'Mitgliedschaften',
                'ordering': ['role', 'user__last_name', 'user__username'],
                'unique_together': {('department', 'user')},
            },
        ),
    ]
