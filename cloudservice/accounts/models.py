"""
User account models for CloudService.
Includes user profiles, storage quotas, and role management.
Django 5.x Features: Enhanced models with new field types.
"""

from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Sum, F
from django.utils.text import slugify
import uuid


class Company(models.Model):
    """Represents a registered company workspace."""

    WORKSPACE_TYPE_CHOICES = [
        ('directory', _('Directory')),
        ('subdomain', _('Subdomain')),
    ]

    HERO_STYLE_CHOICES = [
        ('gradient', _('Gradient')),
        ('image', _('Image')),
        ('video', _('Video')),
    ]

    HEX_COLOR_VALIDATOR = RegexValidator(
        regex=r'^#[0-9A-Fa-f]{6}$',
        message=_('Use a valid hex color like #667EEA.'),
    )

    name = models.CharField(
        max_length=180,
        unique=True,
        verbose_name=_('Company name'),
    )
    slug = models.SlugField(
        max_length=180,
        unique=True,
        verbose_name=_('Company slug'),
    )
    workspace_type = models.CharField(
        max_length=20,
        choices=WORKSPACE_TYPE_CHOICES,
        default='directory',
        verbose_name=_('Workspace type'),
    )
    workspace_key = models.SlugField(
        max_length=63,
        unique=True,
        verbose_name=_('Workspace key'),
        help_text=_('Used for the company directory or subdomain.'),
    )
    included_free_employees = models.PositiveSmallIntegerField(
        default=5,
        verbose_name=_('Included free employees'),
    )

    # Landing page customization
    landing_title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Landing page title'),
        help_text=_('Leave blank to use company name.'),
    )
    landing_subtitle = models.CharField(
        max_length=400,
        blank=True,
        verbose_name=_('Landing page subtitle'),
    )
    landing_logo = models.ImageField(
        upload_to='companies/logos/',
        null=True,
        blank=True,
        verbose_name=_('Company logo'),
    )
    landing_hero_style = models.CharField(
        max_length=20,
        choices=HERO_STYLE_CHOICES,
        default='gradient',
        verbose_name=_('Hero style'),
    )
    landing_hero_image = models.ImageField(
        upload_to='companies/hero/',
        null=True,
        blank=True,
        verbose_name=_('Hero background image'),
    )
    landing_hero_video = models.FileField(
        upload_to='companies/hero/',
        null=True,
        blank=True,
        verbose_name=_('Hero background video'),
    )
    landing_primary_color = models.CharField(
        max_length=7,
        default='#667eea',
        validators=[HEX_COLOR_VALIDATOR],
        verbose_name=_('Primary brand color'),
    )
    landing_secondary_color = models.CharField(
        max_length=7,
        default='#764ba2',
        validators=[HEX_COLOR_VALIDATOR],
        verbose_name=_('Secondary brand color'),
    )
    landing_custom_html = models.TextField(
        blank=True,
        verbose_name=_('Custom HTML block'),
        help_text=_('Additional HTML shown on the landing page.'),
    )
    landing_custom_css = models.TextField(
        blank=True,
        verbose_name=_('Custom CSS'),
        help_text=_('Custom CSS applied on the landing page.'),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at'),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at'),
    )

    class Meta:
        verbose_name = _('Company')
        verbose_name_plural = _('Companies')
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def workspace_label(self):
        if self.workspace_type == 'subdomain':
            return f'{self.workspace_key}.*'
        return f'/{self.workspace_key}/mysite/'

    @property
    def effective_landing_title(self):
        return self.landing_title or self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.workspace_key:
            self.workspace_key = self.slug
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    """
    Extended user profile with storage and quota information.
    """
    ROLE_CHOICES = [
        ('user', _('User')),
        ('admin', _('Administrator')),
        ('moderator', _('Moderator')),
    ]

    LANGUAGE_CHOICES = [
        ('de', 'Deutsch'),
        ('en', 'English'),
        ('fr', 'Français'),
    ]

    DESIGN_VARIANT_CHOICES = [
        ('gradient', _('Gradient')),
        ('minimal', _('Minimal')),
        ('contrast', _('Contrast')),
    ]
    COLOR_PRESET_CHOICES = [
        ('default', _('Default Blue')),
        ('forest', _('Forest')),
        ('sunset', _('Sunset')),
        ('berry', _('Berry')),
        ('slate', _('Slate')),
        ('custom', _('Custom')),
    ]
    MYSITE_HERO_STYLE_CHOICES = [
        ('gradient', _('Gradient')),
        ('image', _('Image')),
        ('video', _('Video')),
    ]
    HEX_COLOR_VALIDATOR = RegexValidator(
        regex=r'^#[0-9A-Fa-f]{6}$',
        message=_('Use a valid hex color like #667EEA.'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('User')
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name=_('Company'),
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='user',
        verbose_name=_('Role')
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Phone number')
    )
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/',
        null=True,
        blank=True,
        verbose_name=_('Avatar')
    )
    bio = models.TextField(
        blank=True,
        verbose_name=_('Bio')
    )
    website = models.URLField(
        blank=True,
        verbose_name=_('Website')
    )
    language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default='de',
        verbose_name=_('Language')
    )
    timezone = models.CharField(
        max_length=63,
        default='Europe/Berlin',
        verbose_name=_('Timezone')
    )
    theme = models.CharField(
        max_length=20,
        choices=[('light', _('Light')), ('dark', _('Dark')), ('auto', _('Auto'))],
        default='auto',
        verbose_name=_('Theme')
    )
    design_variant = models.CharField(
        max_length=20,
        choices=DESIGN_VARIANT_CHOICES,
        default='gradient',
        verbose_name=_('Design variant')
    )
    color_preset = models.CharField(
        max_length=20,
        choices=COLOR_PRESET_CHOICES,
        default='default',
        verbose_name=_('Color preset')
    )
    primary_color = models.CharField(
        max_length=7,
        default='#667eea',
        validators=[HEX_COLOR_VALIDATOR],
        verbose_name=_('Primary color')
    )
    secondary_color = models.CharField(
        max_length=7,
        default='#764ba2',
        validators=[HEX_COLOR_VALIDATOR],
        verbose_name=_('Secondary color')
    )
    mysite_hero_style = models.CharField(
        max_length=20,
        choices=MYSITE_HERO_STYLE_CHOICES,
        default='gradient',
        verbose_name=_('MySite hero style')
    )
    mysite_hero_image = models.ImageField(
        upload_to='mysite/hero/%Y/%m/',
        null=True,
        blank=True,
        verbose_name=_('MySite hero image')
    )
    mysite_hero_video = models.FileField(
        upload_to='mysite/hero/%Y/%m/',
        null=True,
        blank=True,
        verbose_name=_('MySite hero video')
    )

    # Unternehmens-/Verzeichnis-Felder
    job_title = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Job title'),
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Department'),
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Location'),
    )
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_reports',
        verbose_name=_('Manager'),
    )

    # Storage quota
    storage_quota = models.BigIntegerField(
        default=5*1024*1024*1024,  # 5 GB default
        validators=[MinValueValidator(1*1024*1024)],  # Min 1 MB
        verbose_name=_('Storage quota (bytes)'),
        help_text=_('Total storage allowed for this user')
    )

    # Feature flags
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name=_('Email verified')
    )
    is_two_factor_enabled = models.BooleanField(
        default=False,
        verbose_name=_('Two-factor authentication enabled')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is active')
    )

    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )
    last_login_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last login')
    )

    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    def get_storage_used(self):
        """
        Calculate total storage used by user.
        Returns value in bytes.
        """
        from core.models import StorageFile

        used = StorageFile.objects.filter(owner=self.user).aggregate(
            total=Sum('size')
        )['total'] or 0
        return used

    def get_storage_used_mb(self):
        """Get storage used in MB"""
        return self.get_storage_used() / (1024 * 1024)

    def get_storage_used_percentage(self):
        """Get storage usage as percentage"""
        used = self.get_storage_used()
        if self.storage_quota == 0:
            return 0
        return (used / self.storage_quota) * 100

    def get_storage_remaining(self):
        """Get remaining storage in bytes"""
        return self.storage_quota - self.get_storage_used()

    def get_storage_remaining_mb(self):
        """Get remaining storage in MB"""
        return self.get_storage_remaining() / (1024 * 1024)

    def is_storage_full(self):
        """Check if user has reached storage limit"""
        return self.get_storage_used() >= self.storage_quota

    def is_storage_warning(self, threshold_percent=80):
        """Check if user is approaching storage limit"""
        return self.get_storage_used_percentage() >= threshold_percent

    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'

    def is_moderator(self):
        """Check if user is moderator"""
        return self.role in ['admin', 'moderator']

    @classmethod
    def get_color_preset_map(cls):
        return {
            'default': {'primary': '#667eea', 'secondary': '#764ba2'},
            'forest': {'primary': '#2f855a', 'secondary': '#276749'},
            'sunset': {'primary': '#dd6b20', 'secondary': '#c53030'},
            'berry': {'primary': '#b83280', 'secondary': '#702459'},
            'slate': {'primary': '#4a5568', 'secondary': '#1a202c'},
        }


class UserSession(models.Model):
    """
    Track user sessions and login history.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_('User')
    )
    session_key = models.CharField(
        max_length=40,
        unique=True,
        verbose_name=_('Session key'),
        db_index=True
    )
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP address')
    )
    user_agent = models.TextField(
        verbose_name=_('User agent'),
        blank=True
    )
    device_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Device name')
    )
    os_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('OS type'),
        choices=[
            ('windows', _('Windows')),
            ('macos', _('macOS')),
            ('linux', _('Linux')),
            ('ios', _('iOS')),
            ('android', _('Android')),
            ('other', _('Other')),
        ]
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is active')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last activity')
    )
    expires_at = models.DateTimeField(
        verbose_name=_('Expires at')
    )

    class Meta:
        ordering = ['-last_activity']
        verbose_name = _('User Session')
        verbose_name_plural = _('User Sessions')
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"

    def is_expired(self):
        """Check if session is expired"""
        return timezone.now() > self.expires_at


class TwoFactorAuth(models.Model):
    """
    Two-factor authentication settings.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='two_factor_auth',
        verbose_name=_('User')
    )
    is_enabled = models.BooleanField(
        default=False,
        verbose_name=_('Is enabled')
    )
    secret_key = models.CharField(
        max_length=32,
        blank=True,
        verbose_name=_('Secret key')
    )
    backup_codes = models.JSONField(
        default=list,
        verbose_name=_('Backup codes')
    )
    method = models.CharField(
        max_length=20,
        choices=[
            ('totp', _('Time-based OTP (Google Authenticator)')),
            ('sms', _('SMS')),
            ('email', _('Email')),
        ],
        default='totp',
        verbose_name=_('Method')
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Phone number')
    )
    enabled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Enabled at')
    )

    class Meta:
        verbose_name = _('Two-Factor Auth')
        verbose_name_plural = _('Two-Factor Auth')

    def __str__(self):
        return f"{self.user.username} - 2FA ({self.get_method_display()})"


class PasswordReset(models.Model):
    """
    Password reset tokens.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_resets',
        verbose_name=_('User')
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        default=uuid.uuid4,
        verbose_name=_('Token'),
        db_index=True
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name=_('Is used')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    expires_at = models.DateTimeField(
        verbose_name=_('Expires at')
    )

    class Meta:
        verbose_name = _('Password Reset')
        verbose_name_plural = _('Password Resets')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - Reset"

    def is_valid(self):
        """Check if token is valid (not expired and not used)"""
        return not self.is_used and timezone.now() < self.expires_at


class AuditLog(models.Model):
    """
    Audit log for account actions.
    """
    ACTION_CHOICES = [
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('password_change', _('Password change')),
        ('email_change', _('Email change')),
        ('profile_update', _('Profile update')),
        ('2fa_enable', _('2FA enabled')),
        ('2fa_disable', _('2FA disabled')),
        ('permission_grant', _('Permission granted')),
        ('permission_revoke', _('Permission revoked')),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        verbose_name=_('User')
    )
    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        verbose_name=_('Action'),
        db_index=True
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP address')
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User agent')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at'),
        db_index=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()}"
