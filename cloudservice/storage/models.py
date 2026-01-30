"""
Storage-specific models for CloudService.
Extensions to core file management.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Sum
import logging

logger = logging.getLogger(__name__)


class StorageStats(models.Model):
    """
    Cache storage statistics for performance.
    Updated periodically via Celery tasks.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='storage_stats',
        verbose_name=_('User')
    )
    total_files = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total files')
    )
    total_folders = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total folders')
    )
    total_size = models.BigIntegerField(
        default=0,
        verbose_name=_('Total size (bytes)')
    )
    total_versions = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total versions')
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last updated')
    )

    class Meta:
        verbose_name = _('Storage Stats')
        verbose_name_plural = _('Storage Stats')

    def __str__(self):
        return f"{self.user.username} - Stats"

    def get_total_size_mb(self):
        """Get total size in MB"""
        return self.total_size / (1024 * 1024)

    def get_total_size_gb(self):
        """Get total size in GB"""
        return self.total_size / (1024 * 1024 * 1024)


class StorageBackup(models.Model):
    """
    Track storage backups.
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('running', _('Running')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='backups',
        verbose_name=_('User')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status'),
        db_index=True
    )
    total_files = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total files')
    )
    total_size = models.BigIntegerField(
        default=0,
        verbose_name=_('Total size (bytes)')
    )
    backed_up_files = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Backed up files')
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error message')
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Started at')
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Completed at')
    )

    class Meta:
        ordering = ['-started_at']
        verbose_name = _('Storage Backup')
        verbose_name_plural = _('Storage Backups')

    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"

    def get_progress_percent(self):
        """Get backup progress as percentage"""
        if self.total_files == 0:
            return 0
        return (self.backed_up_files / self.total_files) * 100


class TrashBin(models.Model):
    """
    Soft delete - moved to trash instead of permanent deletion.
    """
    from core.models import StorageFile, StorageFolder

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trash',
        verbose_name=_('User')
    )

    # Generic relation to file or folder
    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.contrib.contenttypes.models import ContentType

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

    original_path = models.TextField(
        verbose_name=_('Original path')
    )
    size = models.BigIntegerField(
        verbose_name=_('Size (bytes)')
    )
    deleted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Deleted at'),
        db_index=True
    )
    expires_at = models.DateTimeField(
        verbose_name=_('Expires at (auto-delete)'),
        db_index=True
    )

    class Meta:
        ordering = ['-deleted_at']
        verbose_name = _('Trash Bin')
        verbose_name_plural = _('Trash Bins')

    def __str__(self):
        return f"Deleted: {self.original_path}"

    def is_expired(self):
        """Check if trash item is expired and ready for permanent deletion"""
        return timezone.now() > self.expires_at


class StorageQuotaAlert(models.Model):
    """
    Alert when storage quota is approaching limit.
    """
    ALERT_TYPES = [
        ('warning', _('Warning - 80% used')),
        ('critical', _('Critical - 95% used')),
        ('full', _('Full - 100% used')),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='quota_alerts',
        verbose_name=_('User')
    )
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPES,
        verbose_name=_('Alert type'),
        db_index=True
    )
    usage_percent = models.PositiveIntegerField(
        verbose_name=_('Usage percent')
    )
    is_acknowledged = models.BooleanField(
        default=False,
        verbose_name=_('Is acknowledged'),
        db_index=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Acknowledged at')
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Storage Quota Alert')
        verbose_name_plural = _('Storage Quota Alerts')
        indexes = [
            models.Index(fields=['user', 'is_acknowledged']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_alert_type_display()}"

    def acknowledge(self):
        """Mark alert as acknowledged"""
        self.is_acknowledged = True
        self.acknowledged_at = timezone.now()
        self.save()
