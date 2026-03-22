from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify


class Department(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name='Name')
    slug = models.SlugField(unique=True, max_length=180, blank=True)
    description = models.TextField(blank=True, verbose_name='Beschreibung')
    icon = models.CharField(max_length=60, default='bi-building', verbose_name='Icon (Bootstrap)')
    color = models.CharField(max_length=7, default='#667eea', verbose_name='Farbe (Hex)')
    head = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='headed_departments', verbose_name='Abteilungsleiter',
    )
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='created_departments',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Abteilung'
        verbose_name_plural = 'Abteilungen'
        permissions = [
            ('create_department', 'Kann Abteilungen erstellen'),
            ('manage_any_department', 'Kann beliebige Abteilungen verwalten'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def user_can_manage(self, user):
        """Staff, perm holder, department head, or members with manager/head role can manage."""
        if not user or not user.is_authenticated:
            return False
        if user.has_perm('departments.manage_any_department'):
            return True
        if self.head_id and self.head_id == user.pk:
            return True
        return self.memberships.filter(user=user, role__in=['manager', 'head']).exists()

    @property
    def member_count(self):
        return self.memberships.count()

    @property
    def site_count(self):
        return self.team_sites.count()


class DepartmentMembership(models.Model):
    ROLE_CHOICES = [
        ('member', 'Mitglied'),
        ('manager', 'Manager'),
        ('head', 'Abteilungsleiter'),
    ]
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name='memberships',
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='department_memberships',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['department', 'user']
        ordering = ['role', 'user__last_name', 'user__username']
        verbose_name = 'Mitgliedschaft'
        verbose_name_plural = 'Mitgliedschaften'

    def __str__(self):
        return f'{self.user.username} @ {self.department.name} ({self.role})'
