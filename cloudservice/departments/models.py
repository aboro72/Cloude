import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Company(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name='Firmenname')
    slug = models.SlugField(unique=True, max_length=180, blank=True)
    description = models.TextField(blank=True, verbose_name='Beschreibung')
    domain = models.CharField(max_length=255, blank=True, verbose_name='Hauptdomain')
    allow_domain_signup = models.BooleanField(default=False, verbose_name='Registrierung per Firmen-Domain erlauben')
    owner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='owned_companies', verbose_name='Firmeninhaber',
    )
    admins = models.ManyToManyField(
        User, blank=True, related_name='managed_companies', verbose_name='Firmenadmins',
    )
    is_active = models.BooleanField(default=True, verbose_name='Aktiv')
    employee_limit = models.PositiveIntegerField(default=5, verbose_name='Mitarbeiterlimit kostenlos')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Firma'
        verbose_name_plural = 'Firmen'
        permissions = [
            ('create_company', 'Kann Firmen erstellen'),
            ('manage_any_company', 'Kann beliebige Firmen verwalten'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def employee_count(self):
        return self.user_profiles.filter(user__is_active=True).count()

    @property
    def area_count(self):
        return self.departments.count()

    @property
    def team_count(self):
        return self.team_sites.count()

    @property
    def is_free_tier(self):
        return self.employee_count <= self.employee_limit

    @property
    def seats_remaining(self):
        return max(self.employee_limit - self.employee_count, 0)

    def user_can_manage(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.has_perm('departments.manage_any_company'):
            return True
        if self.owner_id == user.id:
            return True
        return self.admins.filter(pk=user.pk).exists()

    def can_add_employee(self, exclude_user=None):
        qs = self.user_profiles.filter(user__is_active=True)
        if exclude_user is not None:
            qs = qs.exclude(user=exclude_user)
        return qs.count() < self.employee_limit

    def ensure_employee_capacity(self, exclude_user=None):
        if self.can_add_employee(exclude_user=exclude_user):
            return
        raise ValueError(
            f'Die Firma "{self.name}" hat das kostenlose Limit von '
            f'{self.employee_limit} Mitarbeitern erreicht.'
        )

    def normalized_domain(self):
        return (self.domain or '').strip().lower()

    def email_matches_domain(self, email):
        email = (email or '').strip().lower()
        domain = self.normalized_domain()
        if '@' not in email or not domain:
            return False
        return email.split('@', 1)[1] == domain


class Department(models.Model):
    name = models.CharField(max_length=150, verbose_name='Name')
    slug = models.SlugField(max_length=180, blank=True)
    company = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.CASCADE,
        related_name='departments', verbose_name='Firma',
    )
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
        verbose_name = 'Bereich'
        verbose_name_plural = 'Bereiche'
        unique_together = [('company', 'name'), ('company', 'slug')]
        permissions = [
            ('create_department', 'Kann Bereiche erstellen'),
            ('manage_any_department', 'Kann beliebige Bereiche verwalten'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            suffix = 2
            while Department.objects.exclude(pk=self.pk).filter(company=self.company, slug=slug).exists():
                slug = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def user_can_manage(self, user):
        """Staff, perm holder, department head, or members with manager/head role can manage."""
        if not user or not user.is_authenticated:
            return False
        if self.company_id and self.company.user_can_manage(user):
            return True
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
        verbose_name = 'Bereichsmitgliedschaft'
        verbose_name_plural = 'Bereichsmitgliedschaften'

    def __str__(self):
        return f'{self.user.username} @ {self.department.name} ({self.role})'


class CompanyInvitation(models.Model):
    ROLE_CHOICES = [
        ('member', 'Mitarbeiter'),
        ('admin', 'Firmenadmin'),
    ]

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='invitations', verbose_name='Firma',
    )
    email = models.EmailField(verbose_name='E-Mail')
    token = models.CharField(max_length=64, unique=True, blank=True, editable=False)
    invited_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='sent_company_invitations', verbose_name='Eingeladen von',
    )
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='company_invitations', verbose_name='Bereich',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member', verbose_name='Rolle')
    expires_at = models.DateTimeField(verbose_name='Gueltig bis')
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name='Angenommen am')
    accepted_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='accepted_company_invitations', verbose_name='Angenommen von',
    )
    is_active = models.BooleanField(default=True, verbose_name='Aktiv')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Firmeneinladung'
        verbose_name_plural = 'Firmeneinladungen'

    def __str__(self):
        return f'{self.email} -> {self.company.name}'

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(24)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=14)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self):
        return self.is_active and self.accepted_at is None and not self.is_expired

    def matches_email(self, email):
        return (self.email or '').strip().lower() == (email or '').strip().lower()

    def accept(self, user):
        self.company.ensure_employee_capacity(exclude_user=user)
        profile = user.profile
        profile.company = self.company
        if self.department_id and self.department and self.department.company_id == self.company_id:
            profile.department_ref = self.department
        profile.save(update_fields=['company', 'department_ref', 'department'])

        if self.department_id and self.department and self.department.company_id == self.company_id:
            DepartmentMembership.objects.get_or_create(
                department=self.department,
                user=user,
                defaults={'role': 'member'},
            )

        if self.role == 'admin':
            self.company.admins.add(user)

        self.accepted_by = user
        self.accepted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=['accepted_by', 'accepted_at', 'is_active'])
