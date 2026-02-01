"""
Core models for CloudService.
Includes file management, storage structure and file versioning.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.db.models import F, Q, Sum, Count
from django.utils import timezone
from django.conf import settings
import os
import mimetypes
import hashlib
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# Register custom MIME types for plugins
mimetypes.add_type('application/plugin', '.plug')  # Universal plugin format


class TimeStampedModel(models.Model):
    """
    Abstract base model with timestamp fields.
    Django 5.x simplification: Uses built-in DateTimeField
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at'),
        db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at'),
        db_index=True
    )

    class Meta:
        abstract = True


class StorageFolder(TimeStampedModel):
    """
    Represents a folder/directory in the cloud storage.
    Django 5.x Features:
    - CharField with max_length for improved validation
    - ForeignKey with on_delete for cleaner cascade behavior
    """
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='folders',
        verbose_name=_('Owner')
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subfolders',
        verbose_name=_('Parent folder'),
        db_index=True
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_('Folder name'),
        db_index=True
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name=_('Is public'),
        db_index=True
    )
    is_starred = models.BooleanField(
        default=False,
        verbose_name=_('Is starred')
    )

    class Meta:
        unique_together = [['owner', 'parent', 'name']]
        ordering = ['-created_at']
        verbose_name = _('Storage Folder')
        verbose_name_plural = _('Storage Folders')
        indexes = [
            models.Index(fields=['owner', 'parent']),
            models.Index(fields=['owner', 'is_public']),
        ]

    def __str__(self):
        return f"{self.name} (Owner: {self.owner.username})"

    def get_path(self):
        """Get the full path of the folder"""
        if self.parent:
            return f"{self.parent.get_path()}/{self.name}"
        return f"/{self.name}"

    def get_size(self):
        """Calculate total size of folder and contents (MB)"""
        files_size = self.files.aggregate(
            total_size=Sum('file__size')
        )['total_size'] or 0

        # Recursively get subfolders sizes
        subfolders_size = sum(
            subfolder.get_size() for subfolder in self.subfolders.all()
        )
        return files_size + subfolders_size

    def get_file_count(self):
        """Get total number of files in folder and subfolders"""
        count = self.files.count()
        count += sum(
            subfolder.get_file_count() for subfolder in self.subfolders.all()
        )
        return count

    @property
    def breadcrumb(self):
        """Get breadcrumb path for display"""
        path = []
        current = self
        while current:
            path.insert(0, current)
            current = current.parent
        return path


class StorageFile(TimeStampedModel):
    """
    Represents a file in the cloud storage.
    Includes metadata and version management.
    """
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name=_('Owner')
    )
    folder = models.ForeignKey(
        StorageFolder,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name=_('Folder')
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_('File name'),
        db_index=True
    )
    file = models.FileField(
        upload_to='files/%Y/%m/%d/%H%M%S',
        verbose_name=_('File'),
        validators=[
            FileExtensionValidator(
                allowed_extensions=settings.ALLOWED_FILE_EXTENSIONS
            )
        ]
    )
    size = models.BigIntegerField(
        verbose_name=_('File size (bytes)'),
        default=0,
        validators=[MaxValueValidator(settings.FILE_UPLOAD_MAX_MEMORY_SIZE)]
    )
    mime_type = models.CharField(
        max_length=100,
        verbose_name=_('MIME type'),
        blank=True,
        db_index=True
    )
    file_hash = models.CharField(
        max_length=64,
        verbose_name=_('SHA256 hash'),
        blank=True,
        unique=True,
        db_index=True
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name=_('Is public'),
        db_index=True
    )
    is_starred = models.BooleanField(
        default=False,
        verbose_name=_('Is starred')
    )
    version_count = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Version count')
    )
    download_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Download count')
    )
    last_accessed = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last accessed')
    )

    # Trash functionality
    is_trashed = models.BooleanField(
        default=False,
        verbose_name=_('Is in trash'),
        db_index=True
    )
    trashed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Trashed at')
    )
    original_folder = models.ForeignKey(
        'StorageFolder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trashed_files',
        verbose_name=_('Original folder (before trash)')
    )

    class Meta:
        unique_together = [['owner', 'folder', 'name']]
        ordering = ['-created_at']
        verbose_name = _('Storage File')
        verbose_name_plural = _('Storage Files')
        indexes = [
            models.Index(fields=['owner', 'folder']),
            models.Index(fields=['owner', 'is_public']),
            models.Index(fields=['created_at']),
            models.Index(fields=['file_hash']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_size_display()})"

    def save(self, *args, **kwargs):
        """
        Override save to compute file hash and MIME type.
        Django 5.x: Simplified method using Path operations.
        """
        if self.file:
            # Get MIME type
            self.mime_type, _ = mimetypes.guess_type(self.file.name)
            if not self.mime_type:
                self.mime_type = 'application/octet-stream'

            # Get file size
            self.size = self.file.size

            # Generate SHA256 hash
            if not self.file_hash:
                hash_object = hashlib.sha256()

                # For small/empty files, include filename and timestamp to ensure uniqueness
                if self.size < 1024:  # Less than 1KB
                    hash_object.update(self.name.encode('utf-8'))
                    hash_object.update(str(timezone.now()).encode('utf-8'))

                # Hash file content
                for chunk in self.file.chunks():
                    hash_object.update(chunk)

                self.file_hash = hash_object.hexdigest()

        super().save(*args, **kwargs)

    def get_size_display(self):
        """Format file size for display"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.size < 1024.0:
                return f"{self.size:.2f} {unit}"
            self.size /= 1024.0
        return f"{self.size:.2f} TB"

    def get_extension(self):
        """Get file extension"""
        return os.path.splitext(self.name)[1].lstrip('.')

    def get_icon_class(self):
        """Get Bootstrap icon class based on file type"""
        extension = self.get_extension().lower()
        icon_map = {
            'pdf': 'bi-file-pdf',
            'doc': 'bi-file-word',
            'docx': 'bi-file-word',
            'xls': 'bi-file-earmark-spreadsheet',
            'xlsx': 'bi-file-earmark-spreadsheet',
            'ppt': 'bi-file-powerpoint',
            'pptx': 'bi-file-powerpoint',
            'jpg': 'bi-file-image',
            'jpeg': 'bi-file-image',
            'png': 'bi-file-image',
            'gif': 'bi-file-image',
            'mp4': 'bi-file-play',
            'avi': 'bi-file-play',
            'mov': 'bi-file-play',
            'mp3': 'bi-file-music',
            'wav': 'bi-file-music',
            'zip': 'bi-file-zip',
            'rar': 'bi-file-zip',
            'txt': 'bi-file-text',
            'py': 'bi-file-code',
            'js': 'bi-file-code',
            'html': 'bi-file-code',
            'css': 'bi-file-code',
        }
        return icon_map.get(extension, 'bi-file-earmark')

    def increment_download_count(self):
        """Increment download counter"""
        self.download_count = F('download_count') + 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['download_count', 'last_accessed'])

    @classmethod
    def duplicate_check(cls, file_hash):
        """Check if file with same hash already exists"""
        return cls.objects.filter(file_hash=file_hash).exists()

    def move_to_trash(self):
        """Move file to trash (soft delete)"""
        self.original_folder = self.folder
        self.is_trashed = True
        self.trashed_at = timezone.now()
        self.save(update_fields=['original_folder', 'is_trashed', 'trashed_at'])

    def restore_from_trash(self):
        """Restore file from trash"""
        if self.original_folder:
            self.folder = self.original_folder
        self.is_trashed = False
        self.trashed_at = None
        self.original_folder = None
        self.save(update_fields=['folder', 'is_trashed', 'trashed_at', 'original_folder'])

    def permanent_delete(self):
        """Permanently delete file and its physical file"""
        if self.file:
            self.file.delete(save=False)
        self.delete()


class FileVersion(TimeStampedModel):
    """
    Represents a version of a file.
    Allows file recovery and version history.
    """
    file = models.ForeignKey(
        StorageFile,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name=_('File')
    )
    version_number = models.PositiveIntegerField(
        verbose_name=_('Version number'),
        db_index=True
    )
    file_data = models.FileField(
        upload_to='versions/%Y/%m/%d/',
        verbose_name=_('Version file')
    )
    file_hash = models.CharField(
        max_length=64,
        verbose_name=_('File hash'),
        db_index=True
    )
    size = models.BigIntegerField(
        verbose_name=_('File size (bytes)'),
        default=0
    )
    change_description = models.TextField(
        blank=True,
        verbose_name=_('Change description')
    )
    is_current = models.BooleanField(
        default=True,
        verbose_name=_('Is current version'),
        db_index=True
    )

    class Meta:
        ordering = ['-version_number']
        verbose_name = _('File Version')
        verbose_name_plural = _('File Versions')
        unique_together = [['file', 'version_number']]
        indexes = [
            models.Index(fields=['file', 'is_current']),
        ]

    def __str__(self):
        return f"{self.file.name} - v{self.version_number}"

    def save(self, *args, **kwargs):
        """Save version and update parent file version count"""
        is_new = not self.pk
        super().save(*args, **kwargs)

        if is_new:
            # Update file version count
            StorageFile.objects.filter(pk=self.file.pk).update(
                version_count=Count('versions')
            )


class ActivityLog(TimeStampedModel):
    """
    Logs user activities on files and folders.
    Useful for audit trail and analytics.
    """
    ACTIVITY_CHOICES = [
        ('upload', _('Upload')),
        ('download', _('Download')),
        ('delete', _('Delete')),
        ('rename', _('Rename')),
        ('move', _('Move')),
        ('share', _('Share')),
        ('unshare', _('Unshare')),
        ('view', _('View')),
        ('create_folder', _('Create Folder')),
        ('permission_change', _('Permission Change')),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        verbose_name=_('User')
    )
    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_CHOICES,
        verbose_name=_('Activity type'),
        db_index=True
    )
    file = models.ForeignKey(
        StorageFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name=_('File')
    )
    folder = models.ForeignKey(
        StorageFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name=_('Folder')
    )
    description = models.TextField(
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

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Activity Log')
        verbose_name_plural = _('Activity Logs')
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['activity_type']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()}"


class Notification(models.Model):
    """
    User notifications for various events.
    """
    NOTIFICATION_TYPES = [
        ('share', _('File shared with you')),
        ('unshare', _('Shared access removed')),
        ('permission_change', _('Permission changed')),
        ('storage_limit', _('Storage limit warning')),
        ('file_deleted', _('File deleted')),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('User')
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        verbose_name=_('Type')
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_('Title')
    )
    message = models.TextField(
        verbose_name=_('Message')
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name=_('Is read'),
        db_index=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at'),
        db_index=True
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expires at')
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    @classmethod
    def create_notification(cls, user, notification_type, title, message, expires_hours=None):
        """Factory method to create notifications"""
        expires_at = None
        if expires_hours:
            expires_at = timezone.now() + timedelta(hours=expires_hours)

        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            expires_at=expires_at
        )
