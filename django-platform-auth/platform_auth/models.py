from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""

    def create_user(self, email, username, password=None, **extra_fields):
        """
        Create and save a regular user.
        """
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        """
        Create and save a superuser.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Unified user model for the platform.
    Combines features from multiple applications:
    - HelpDesk: custom user model with roles and email-based login
    - Cloude: storage quota and preferences
    """

    # Basic fields
    username = models.CharField(
        max_length=80,
        unique=True,
        db_index=True,
        verbose_name=_('username')
    )
    email = models.EmailField(
        max_length=120,
        unique=True,
        db_index=True,
        verbose_name=_('email address')
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name=_('first name')
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name=_('last name')
    )

    # Role system (HelpDesk + Cloude combined)
    ROLE_CHOICES = [
        ('admin', _('Administrator')),
        ('support_agent', _('Support Agent')),
        ('customer', _('Customer')),
        ('user', _('Regular User')),
        ('moderator', _('Moderator')),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='user',
        verbose_name=_('role')
    )
    support_level = models.IntegerField(
        null=True,
        blank=True,
        choices=[(i, f'Level {i}') for i in range(1, 5)],
        verbose_name=_('support level'),
        help_text=_('1=Basic, 2=Technical, 3=Expert, 4=Senior')
    )

    # Storage quota (from Cloude UserProfile)
    storage_quota = models.BigIntegerField(
        default=5*1024*1024*1024,  # 5 GB default
        verbose_name=_('storage quota (bytes)'),
        help_text=_('Maximum storage allowed for this user')
    )

    # Profile fields (merged from both)
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('phone number')
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('department')
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('location')
    )
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/',
        null=True,
        blank=True,
        verbose_name=_('avatar')
    )
    bio = models.TextField(
        blank=True,
        verbose_name=_('biography')
    )
    website = models.URLField(
        blank=True,
        verbose_name=_('website')
    )

    # Address (from HelpDesk)
    street = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_('street address')
    )
    postal_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name=_('postal code')
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('city')
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default='Germany',
        verbose_name=_('country')
    )

    # Preferences (from Cloude)
    LANGUAGE_CHOICES = [
        ('de', _('German')),
        ('en', _('English')),
        ('fr', _('French')),
    ]
    language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default='de',
        verbose_name=_('language')
    )

    timezone = models.CharField(
        max_length=63,
        default='Europe/Berlin',
        verbose_name=_('timezone')
    )

    THEME_CHOICES = [
        ('light', _('Light')),
        ('dark', _('Dark')),
        ('auto', _('Auto')),
    ]
    theme = models.CharField(
        max_length=20,
        choices=THEME_CHOICES,
        default='auto',
        verbose_name=_('theme')
    )

    # Microsoft OAuth (from HelpDesk)
    microsoft_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Microsoft ID')
    )
    microsoft_token = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Microsoft token')
    )

    # Status fields (merged)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_('active')
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name=_('staff status')
    )
    email_verified = models.BooleanField(
        default=False,
        verbose_name=_('email verified')
    )
    is_two_factor_enabled = models.BooleanField(
        default=False,
        verbose_name=_('two factor enabled')
    )
    force_password_change = models.BooleanField(
        default=False,
        verbose_name=_('force password change'),
        help_text=_('User must change password on next login')
    )

    # Activity tracking
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('last login')
    )
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('last activity')
    )

    # Timestamps
    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name=_('created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('updated at')
    )

    # App-specific settings (JSONField for extensibility)
    app_settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('app settings'),
        help_text=_('App-specific settings and feature flags')
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        db_table = 'platform_users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['role']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Return the user's short name."""
        return self.first_name

    def is_admin(self):
        """Check if user is admin."""
        return self.role == 'admin' or self.is_superuser

    def is_support_agent(self):
        """Check if user is support agent."""
        return self.role == 'support_agent'

    def is_customer(self):
        """Check if user is customer."""
        return self.role == 'customer'

    def is_moderator(self):
        """Check if user is moderator."""
        return self.role == 'moderator'

    def get_storage_percentage(self):
        """Get storage usage percentage (for apps that support it)."""
        if self.storage_quota == 0:
            return 0
        # This method should be overridden by the app that manages storage
        return 0

    @property
    def is_online(self):
        """Check if user is online based on last activity."""
        if not self.last_activity:
            return False
        from datetime import timedelta
        return (timezone.now() - self.last_activity) < timedelta(minutes=5)

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
