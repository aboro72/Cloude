"""
Clock Dashboard Widget.

Displays a mini analog clock on the landing page dashboard.
"""

from typing import Dict, Any
from plugins.widgets import DashboardWidgetProvider
import logging

logger = logging.getLogger(__name__)


class ClockWidgetProvider(DashboardWidgetProvider):
    """Dashboard widget showing an animated mini clock."""

    widget_id = "clock_widget"
    widget_name = "Uhr"
    widget_icon = "bi-clock"
    widget_size = "small"
    widget_order = 5  # Show first

    def get_context(self, request) -> Dict[str, Any]:
        """Get context for the clock widget."""
        return {
            'show_digital': True,
            'timezone': request.user.profile.timezone if hasattr(request.user, 'profile') else 'Europe/Berlin',
        }

    def get_template_name(self) -> str:
        return 'clock_preview/widget.html'
