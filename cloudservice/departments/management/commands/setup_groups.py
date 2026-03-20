"""
Management command: python manage.py setup_groups

Creates the standard CloudService permission groups with the correct Django permissions.
Safe to run multiple times (idempotent).

Groups:
  Administratoren  – full app-level access (no is_superuser needed)
  Abteilungsleiter – create/manage departments, create team sites, write news
  Redakteure       – create/edit/delete news articles
  Team-Manager     – create/manage own team sites, write team news
  Mitarbeiter      – authenticated read access (no extra permissions needed)
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


# Permission codenames grouped by model label
GROUPS = {
    'Administratoren': {
        'departments.department': [
            'add_department', 'change_department', 'delete_department', 'view_department',
            'create_department', 'manage_any_department',
        ],
        'departments.departmentmembership': [
            'add_departmentmembership', 'change_departmentmembership', 'delete_departmentmembership', 'view_departmentmembership',
        ],
        'sharing.groupshare': [
            'add_groupshare', 'change_groupshare', 'delete_groupshare', 'view_groupshare',
            'create_groupshare', 'manage_any_groupshare',
        ],
        'news.newsarticle': [
            'add_newsarticle', 'change_newsarticle', 'delete_newsarticle', 'view_newsarticle',
        ],
        'news.newscategory': [
            'add_newscategory', 'change_newscategory', 'delete_newscategory',
        ],
    },
    'Abteilungsleiter': {
        'departments.department': [
            'add_department', 'change_department', 'view_department',
            'create_department', 'manage_any_department',
        ],
        'departments.departmentmembership': [
            'add_departmentmembership', 'change_departmentmembership', 'delete_departmentmembership', 'view_departmentmembership',
        ],
        'sharing.groupshare': [
            'add_groupshare', 'change_groupshare', 'view_groupshare',
            'create_groupshare',
        ],
        'news.newsarticle': [
            'add_newsarticle', 'change_newsarticle', 'view_newsarticle',
        ],
    },
    'Redakteure': {
        'news.newsarticle': [
            'add_newsarticle', 'change_newsarticle', 'delete_newsarticle', 'view_newsarticle',
        ],
        'news.newscategory': [
            'add_newscategory', 'change_newscategory', 'view_newscategory',
        ],
    },
    'Team-Manager': {
        'sharing.groupshare': [
            'add_groupshare', 'change_groupshare', 'view_groupshare',
            'create_groupshare',
        ],
        'news.newsarticle': [
            'add_newsarticle', 'change_newsarticle', 'view_newsarticle',
        ],
    },
    'Mitarbeiter': {},  # Authenticated read-only; no extra permissions needed
}


class Command(BaseCommand):
    help = 'Creates standard CloudService permission groups (idempotent).'

    def handle(self, *args, **options):
        created_groups = 0
        updated_groups = 0

        for group_name, model_perms in GROUPS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                created_groups += 1
                self.stdout.write(f'  + Gruppe erstellt: {group_name}')
            else:
                updated_groups += 1
                self.stdout.write(f'  ~ Gruppe aktualisiert: {group_name}')

            perms_to_assign = []
            for model_label, codenames in model_perms.items():
                app_label, model_name = model_label.split('.')
                try:
                    ct = ContentType.objects.get(app_label=app_label, model=model_name)
                except ContentType.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'    [!] ContentType nicht gefunden: {model_label} - uebersprungen')
                    )
                    continue

                for codename in codenames:
                    try:
                        perm = Permission.objects.get(content_type=ct, codename=codename)
                        perms_to_assign.append(perm)
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'    [!] Permission nicht gefunden: {model_label}.{codename} - uebersprungen')
                        )

            group.permissions.set(perms_to_assign)

        self.stdout.write(self.style.SUCCESS(
            f'\nFertig: {created_groups} Gruppe(n) erstellt, {updated_groups} aktualisiert.'
        ))
        self.stdout.write('\nGruppen-Übersicht:')
        for g in Group.objects.all().order_by('name'):
            count = g.user_set.count()
            perms = g.permissions.count()
            self.stdout.write(f'  {g.name:<20} {perms:>3} Berechtigungen, {count:>3} Nutzer')
