"""
Storage Stats Widget - Shows user's storage usage statistics.
"""

from typing import Dict, Any
from plugins.widgets import DashboardWidgetProvider


class StorageStatsWidget(DashboardWidgetProvider):
    """Widget displaying user's storage statistics."""

    widget_id = "storage_stats"
    widget_name = "Speicherplatz"
    widget_icon = "bi-hdd"
    widget_size = "medium"
    widget_order = 10

    def get_context(self, request) -> Dict[str, Any]:
        """Get storage statistics for the current user."""
        from core.models import StorageFile, StorageFolder

        profile = request.user.profile

        total_files = StorageFile.objects.filter(owner=request.user).count()
        total_folders = StorageFolder.objects.filter(owner=request.user).count()

        storage_used_bytes = profile.get_storage_used()
        storage_quota_bytes = profile.storage_quota

        # Convert to readable units
        storage_used_mb = storage_used_bytes / (1024 * 1024)
        storage_quota_gb = storage_quota_bytes / (1024 * 1024 * 1024)

        # Calculate percentage
        if storage_quota_bytes > 0:
            percentage = (storage_used_bytes / storage_quota_bytes) * 100
        else:
            percentage = 0

        return {
            'total_files': total_files,
            'total_folders': total_folders,
            'storage_used_mb': storage_used_mb,
            'storage_quota_gb': storage_quota_gb,
            'storage_percentage': percentage,
            'is_warning': percentage >= 80,
            'is_critical': percentage >= 95,
        }

    def get_template_name(self) -> str:
        return 'core/widgets/storage_stats.html'
