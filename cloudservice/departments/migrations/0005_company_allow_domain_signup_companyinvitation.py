from datetime import timedelta

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def default_invitation_expiry():
    return timezone.now() + timedelta(days=14)


class Migration(migrations.Migration):

    dependencies = [
        ('departments', '0004_alter_company_options_company_admins_company_domain_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='allow_domain_signup',
            field=models.BooleanField(default=False, verbose_name='Registrierung per Firmen-Domain erlauben'),
        ),
        migrations.CreateModel(
            name='CompanyInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, verbose_name='E-Mail')),
                ('token', models.CharField(blank=True, editable=False, max_length=64, unique=True)),
                ('role', models.CharField(choices=[('member', 'Mitarbeiter'), ('admin', 'Firmenadmin')], default='member', max_length=20, verbose_name='Rolle')),
                ('expires_at', models.DateTimeField(default=default_invitation_expiry, verbose_name='Gueltig bis')),
                ('accepted_at', models.DateTimeField(blank=True, null=True, verbose_name='Angenommen am')),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktiv')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('accepted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='accepted_company_invitations', to=settings.AUTH_USER_MODEL, verbose_name='Angenommen von')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='departments.company', verbose_name='Firma')),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='company_invitations', to='departments.department', verbose_name='Bereich')),
                ('invited_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_company_invitations', to=settings.AUTH_USER_MODEL, verbose_name='Eingeladen von')),
            ],
            options={
                'verbose_name': 'Firmeneinladung',
                'verbose_name_plural': 'Firmeneinladungen',
                'ordering': ['-created_at'],
            },
        ),
    ]
