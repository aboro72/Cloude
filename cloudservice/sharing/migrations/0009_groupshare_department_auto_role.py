from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('departments', '0002_department_permissions'),
        ('sharing', '0008_groupshare_permissions'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupShareDepartmentAutoRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('preexisting_member', models.BooleanField(default=False)),
                ('preexisting_team_leader', models.BooleanField(default=False)),
                ('added_to_members', models.BooleanField(default=False)),
                ('added_to_team_leaders', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_site_auto_roles', to='departments.department', verbose_name='Abteilung')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='department_auto_roles', to='sharing.groupshare', verbose_name='Group')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_share_department_auto_roles', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Team-Site Auto Role',
                'verbose_name_plural': 'Team-Site Auto Roles',
                'indexes': [
                    models.Index(fields=['group', 'department'], name='sharing_gro_group_i_89c679_idx'),
                    models.Index(fields=['user'], name='sharing_gro_user_id_1a1471_idx'),
                ],
                'unique_together': {('group', 'department', 'user')},
            },
        ),
    ]

