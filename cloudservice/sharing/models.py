"""
Sharing and collaboration models for CloudService.
Includes file sharing, permissions, and public links.
"""

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator
import uuid
import secrets
from datetime import timedelta


def generate_public_link_token():
    """Generate a secure token for public links"""
    return secrets.token_urlsafe(24)


class SharePermission(models.Model):
    """
    Custom permission levels for shared resources.
    Renamed to SharePermission to avoid conflict with Django's auth.Permission
    """
    PERMISSION_CHOICES = [
        ('view', _('View only')),
        ('download', _('Download')),
        ('edit', _('Edit')),
        ('delete', _('Delete')),
        ('share', _('Share')),
        ('admin', _('Admin')),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='share_permissions',
        verbose_name=_('User')
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='share_permissions',
        verbose_name=_('Content type')
    )
    object_id = models.PositiveIntegerField(
        verbose_name=_('Object ID')
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    permission_type = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        verbose_name=_('Permission type'),
        db_index=True
    )
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_share_permissions',
        verbose_name=_('Granted by')
    )
    granted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Granted at')
    )

    class Meta:
        verbose_name = _('Share Permission')
        verbose_name_plural = _('Share Permissions')
        unique_together = [['user', 'content_type', 'object_id', 'permission_type']]
        ordering = ['-granted_at']
        indexes = [
            models.Index(fields=['user', 'permission_type']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_permission_type_display()}"


class UserShare(models.Model):
    """
    Direct user-to-user sharing.
    Share files/folders with specific users.
    """
    from core.models import StorageFile, StorageFolder

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shares_created',
        verbose_name=_('Owner')
    )
    shared_with = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shares_received',
        verbose_name=_('Shared with')
    )

    # Generic relation to file or folder
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_('Content type'),
        limit_choices_to={'model__in': ['storagefile', 'storagefolder']}
    )
    object_id = models.PositiveIntegerField(
        verbose_name=_('Object ID')
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    permission = models.CharField(
        max_length=20,
        choices=SharePermission.PERMISSION_CHOICES,
        default='view',
        verbose_name=_('Permission'),
        db_index=True
    )

    message = models.TextField(
        blank=True,
        verbose_name=_('Share message')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is active'),
        db_index=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )

    class Meta:
        verbose_name = _('User Share')
        verbose_name_plural = _('User Shares')
        unique_together = [['owner', 'shared_with', 'content_type', 'object_id']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['shared_with', 'is_active']),
        ]

    def __str__(self):
        return f"{self.owner.username} → {self.shared_with.username}"

    def can_view(self):
        return self.permission in ['view', 'download', 'edit', 'delete', 'share', 'admin']

    def can_download(self):
        return self.permission in ['download', 'edit', 'delete', 'share', 'admin']

    def can_edit(self):
        return self.permission in ['edit', 'delete', 'share', 'admin']

    def can_delete(self):
        return self.permission in ['delete', 'share', 'admin']

    def can_share(self):
        return self.permission in ['share', 'admin']

    def can_admin(self):
        return self.permission == 'admin'


class PublicLink(models.Model):
    """
    Public shareable links for files and folders.
    Can be password protected and have expiration dates.
    """
    from core.models import StorageFile, StorageFolder

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='public_links',
        verbose_name=_('Owner')
    )

    # Generic relation to file or folder
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_('Content type'),
        limit_choices_to={'model__in': ['storagefile', 'storagefolder']}
    )
    object_id = models.PositiveIntegerField(
        verbose_name=_('Object ID')
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    token = models.CharField(
        max_length=32,
        unique=True,
        default=generate_public_link_token,
        verbose_name=_('Token'),
        db_index=True
    )
    password_hash = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Password hash')
    )
    permission = models.CharField(
        max_length=20,
        choices=SharePermission.PERMISSION_CHOICES,
        default='view',
        verbose_name=_('Permission')
    )

    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Title')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )

    # Expiration
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expires at')
    )
    expires_after_downloads = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name=_('Expires after N downloads')
    )

    # Access control
    allow_download = models.BooleanField(
        default=True,
        verbose_name=_('Allow download')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is active'),
        db_index=True
    )

    # Analytics
    view_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('View count')
    )
    download_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Download count')
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

    class Meta:
        verbose_name = _('Public Link')
        verbose_name_plural = _('Public Links')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['token']),
        ]

    def __str__(self):
        return f"Public link - {self.token[:8]}..."

    def is_expired(self):
        """Check if link is expired"""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        if self.expires_after_downloads and self.download_count >= self.expires_after_downloads:
            return True
        return False

    def set_password(self, password):
        """Set password for the link"""
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(password)

    def check_password(self, password):
        """Check if password matches"""
        from django.contrib.auth.hashers import check_password
        return check_password(password, self.password_hash)

    def increment_view_count(self):
        """Increment view counter"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

    def increment_download_count(self):
        """Increment download counter"""
        self.download_count += 1
        self.save(update_fields=['download_count'])

    def get_url(self):
        """Generate public link URL"""
        return f"/share/{self.token}/"


class GroupShare(models.Model):
    """
    Group-based sharing for teams.
    """
    from core.models import StorageFile, StorageFolder

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='group_shares_created',
        verbose_name=_('Owner')
    )
    group_name = models.CharField(
        max_length=255,
        verbose_name=_('Group name')
    )
    members = models.ManyToManyField(
        User,
        related_name='group_shares_member_of',
        verbose_name=_('Members')
    )

    # Generic relation to file or folder
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_('Content type'),
        limit_choices_to={'model__in': ['storagefile', 'storagefolder']}
    )
    object_id = models.PositiveIntegerField(
        verbose_name=_('Object ID')
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    permission = models.CharField(
        max_length=20,
        choices=SharePermission.PERMISSION_CHOICES,
        default='view',
        verbose_name=_('Permission')
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is active')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )

    class Meta:
        verbose_name = _('Group Share')
        verbose_name_plural = _('Group Shares')
        ordering = ['-created_at']

    def __str__(self):
        return f"Group: {self.group_name}"


class ShareLog(models.Model):
    """
    Log of share activities.
    """
    ACTION_CHOICES = [
        ('created', _('Created')),
        ('updated', _('Updated')),
        ('deleted', _('Deleted')),
        ('accessed', _('Accessed')),
        ('downloaded', _('Downloaded')),
        ('password_changed', _('Password changed')),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='share_logs',
        verbose_name=_('User')
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name=_('Action'),
        db_index=True
    )

    # Generic relation
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_('Content type')
    )
    object_id = models.PositiveIntegerField(
        verbose_name=_('Object ID')
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP address')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at'),
        db_index=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Share Log')
        verbose_name_plural = _('Share Logs')
        indexes = [
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.created_at}"
