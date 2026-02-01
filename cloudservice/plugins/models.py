"""
Plugin system data models.

Stores plugin metadata, state, and operation logs.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Plugin(models.Model):
    """
    Stores plugin metadata and state.

    Represents a installed CloudService plugin with version control,
    state management, and error tracking.
    """

    # Status choices
    STATUS_CHOICES = [
        ('inactive', _('Inactive')),
        ('active', _('Active')),
        ('error', _('Error')),
    ]

    # Identity
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Display name of the plugin"
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text="URL-friendly identifier"
    )

    # Metadata
    version = models.CharField(
        max_length=50,
        help_text="Plugin version (e.g., 1.0.0)"
    )
    author = models.CharField(
        max_length=255,
        help_text="Plugin author name"
    )
    description = models.TextField(
        help_text="Plugin description"
    )

    # Files
    zip_file = models.FileField(
        upload_to='plugins/%Y/%m/',
        blank=True,
        null=True,
        help_text="Uploaded ZIP file (optional for local folder plugins)"
    )
    extracted_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Path where plugin files are located"
    )
    is_local = models.BooleanField(
        default=False,
        help_text="True if plugin is a local folder (not uploaded ZIP)"
    )

    # Manifest (parsed from plugin.json)
    manifest = models.JSONField(
        default=dict,
        help_text="Plugin manifest data from plugin.json"
    )

    # State
    enabled = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether plugin is enabled"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='inactive',
        db_index=True,
        help_text="Current status of the plugin"
    )

    # Module path (e.g., 'plugins.installed.markdown_preview')
    module_name = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Python module name for dynamic importing"
    )

    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Error message if plugin failed to load"
    )

    # Position on file preview page
    POSITION_CHOICES = [
        ('left', _('Left')),
        ('center', _('Center')),
        ('right', _('Right')),
    ]
    position = models.CharField(
        max_length=20,
        choices=POSITION_CHOICES,
        default='left',
        help_text="Position on file preview page (left, center, or right)"
    )

    # Metadata
    installed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installed_plugins',
        help_text="Admin who uploaded this plugin"
    )

    # Plugin settings (configurable by admin)
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Plugin-specific configuration settings"
    )
    settings_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON schema defining available settings"
    )
    has_settings = models.BooleanField(
        default=False,
        help_text="Whether this plugin has configurable settings"
    )

    # Timestamps
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When plugin was uploaded"
    )
    activated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When plugin was last activated"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last modification time"
    )

    def get_setting(self, key, default=None):
        """Get a specific setting value."""
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        """Set a specific setting value."""
        self.settings[key] = value
        self.save(update_fields=['settings'])

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = _('Plugin')
        verbose_name_plural = _('Plugins')
        indexes = [
            models.Index(fields=['status', 'enabled']),
            models.Index(fields=['module_name']),
        ]

    def __str__(self):
        return f"{self.name} v{self.version}"

    @property
    def get_status_display_styled(self):
        """Return status with color coding"""
        colors = {
            'active': '🟢 Active',
            'inactive': '⚫ Inactive',
            'error': '🔴 Error',
        }
        return colors.get(self.status, self.get_status_display())


class PluginLog(models.Model):
    """
    Audit log for plugin operations.

    Tracks all plugin-related actions (upload, activate, deactivate, errors)
    for audit purposes.
    """

    # Action choices
    ACTION_CHOICES = [
        ('uploaded', _('Uploaded')),
        ('activated', _('Activated')),
        ('deactivated', _('Deactivated')),
        ('error', _('Error')),
    ]

    # Reference
    plugin = models.ForeignKey(
        Plugin,
        on_delete=models.CASCADE,
        related_name='logs',
        help_text="Plugin this log entry is for"
    )

    # Action details
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        db_index=True,
        help_text="Type of action performed"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plugin_actions',
        help_text="Admin who performed the action"
    )

    # Message
    message = models.TextField(
        help_text="Detailed message about the action"
    )

    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the action occurred"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Plugin Log')
        verbose_name_plural = _('Plugin Logs')

    def __str__(self):
        return f"{self.plugin.name}: {self.action} at {self.created_at}"
