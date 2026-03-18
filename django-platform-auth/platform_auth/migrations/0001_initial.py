# Generated migration file

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(db_index=True, max_length=80, unique=True, verbose_name='username')),
                ('email', models.EmailField(db_index=True, max_length=120, unique=True, verbose_name='email address')),
                ('first_name', models.CharField(max_length=100, verbose_name='first name')),
                ('last_name', models.CharField(max_length=100, verbose_name='last name')),
                ('role', models.CharField(choices=[('admin', 'Administrator'), ('support_agent', 'Support Agent'), ('customer', 'Customer'), ('user', 'Regular User'), ('moderator', 'Moderator')], default='user', max_length=20, verbose_name='role')),
                ('support_level', models.IntegerField(blank=True, choices=[(1, 'Level 1'), (2, 'Level 2'), (3, 'Level 3'), (4, 'Level 4')], null=True, verbose_name='support level')),
                ('storage_quota', models.BigIntegerField(default=5368709120, help_text='Maximum storage allowed for this user', verbose_name='storage quota (bytes)')),
                ('phone', models.CharField(blank=True, max_length=20, null=True, verbose_name='phone number')),
                ('department', models.CharField(blank=True, max_length=100, null=True, verbose_name='department')),
                ('location', models.CharField(blank=True, max_length=100, null=True, verbose_name='location')),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/%Y/%m/', verbose_name='avatar')),
                ('bio', models.TextField(blank=True, verbose_name='biography')),
                ('website', models.URLField(blank=True, verbose_name='website')),
                ('street', models.CharField(blank=True, max_length=200, null=True, verbose_name='street address')),
                ('postal_code', models.CharField(blank=True, max_length=10, null=True, verbose_name='postal code')),
                ('city', models.CharField(blank=True, max_length=100, null=True, verbose_name='city')),
                ('country', models.CharField(blank=True, default='Germany', max_length=100, null=True, verbose_name='country')),
                ('language', models.CharField(choices=[('de', 'German'), ('en', 'English'), ('fr', 'French')], default='de', max_length=5, verbose_name='language')),
                ('timezone', models.CharField(default='Europe/Berlin', max_length=63, verbose_name='timezone')),
                ('theme', models.CharField(choices=[('light', 'Light'), ('dark', 'Dark'), ('auto', 'Auto')], default='auto', max_length=20, verbose_name='theme')),
                ('microsoft_id', models.CharField(blank=True, db_index=True, max_length=100, null=True, unique=True, verbose_name='Microsoft ID')),
                ('microsoft_token', models.TextField(blank=True, null=True, verbose_name='Microsoft token')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='active')),
                ('is_staff', models.BooleanField(default=False, verbose_name='staff status')),
                ('email_verified', models.BooleanField(default=False, verbose_name='email verified')),
                ('is_two_factor_enabled', models.BooleanField(default=False, verbose_name='two factor enabled')),
                ('force_password_change', models.BooleanField(default=False, help_text='User must change password on next login', verbose_name='force password change')),
                ('last_activity', models.DateTimeField(blank=True, null=True, verbose_name='last activity')),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('app_settings', models.JSONField(blank=True, default=dict, help_text='App-specific settings and feature flags', verbose_name='app settings')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'db_table': 'platform_users',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['email'], name='platform_u_email_abc123_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['username'], name='platform_u_usernam_def456_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['role'], name='platform_u_role_ghi789_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['created_at'], name='platform_u_created_jkl012_idx'),
        ),
    ]
