"""
Recent Files Widget - Shows user's most recently uploaded files.
"""

from typing import Dict, Any
from plugins.widgets import DashboardWidgetProvider


class RecentFilesWidget(DashboardWidgetProvider):
    """Widget displaying user's recent files."""

    widget_id = "recent_files"
    widget_name = "Letzte Dateien"
    widget_icon = "bi-file-earmark-text"
    widget_size = "medium"
    widget_order = 20

    def get_context(self, request) -> Dict[str, Any]:
        """Get recent files for the current user."""
        from core.models import StorageFile

        recent_files = StorageFile.objects.filter(
            owner=request.user
        ).order_by('-created_at')[:5]

        return {
            'recent_files': recent_files,
        }

    def get_template_name(self) -> str:
        return 'core/widgets/recent_files.html'
