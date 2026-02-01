"""
Widget Provider base class for dashboard widgets.

Plugins can implement DashboardWidgetProvider to add widgets to the landing page.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DashboardWidgetProvider(ABC):
    """
    Abstract base class for dashboard widgets.

    Plugins should subclass this and register with the UI_DASHBOARD_WIDGET hook.
    """

    # Widget identification
    widget_id: str = ""  # Unique identifier (e.g., 'clock_widget')
    widget_name: str = ""  # Display name (e.g., 'Analog Clock')
    widget_icon: str = "bi-grid"  # Bootstrap icon class

    # Widget layout
    widget_size: str = "medium"  # 'small' (4 cols), 'medium' (6 cols), 'large' (12 cols)
    widget_order: int = 100  # Lower = appears first

    @abstractmethod
    def get_context(self, request) -> Dict[str, Any]:
        """
        Get context data for rendering the widget.

        Args:
            request: The HTTP request object

        Returns:
            Dictionary of context variables for the template
        """
        pass

    @abstractmethod
    def get_template_name(self) -> str:
        """
        Get the template path for this widget.

        Returns:
            Template path (e.g., 'clock_preview/widget.html')
        """
        pass

    def is_visible(self, request) -> bool:
        """
        Check if this widget should be shown to the current user.

        Override this to implement permission checks or feature flags.

        Args:
            request: The HTTP request object

        Returns:
            True if widget should be displayed
        """
        return True

    def get_css_classes(self) -> str:
        """
        Get Bootstrap column classes based on widget size.

        Returns:
            CSS classes for the widget container
        """
        size_map = {
            'small': 'col-md-4',
            'medium': 'col-md-6',
            'large': 'col-md-12',
        }
        return size_map.get(self.widget_size, 'col-md-6')

    def render(self, request) -> Optional[Dict[str, Any]]:
        """
        Prepare widget data for rendering.

        Returns:
            Dictionary with widget metadata and context, or None if not visible
        """
        if not self.is_visible(request):
            return None

        try:
            context = self.get_context(request)
            return {
                'id': self.widget_id,
                'name': self.widget_name,
                'icon': self.widget_icon,
                'size': self.widget_size,
                'order': self.widget_order,
                'css_classes': self.get_css_classes(),
                'template': self.get_template_name(),
                'context': context,
            }
        except Exception as e:
            logger.error(f"Widget {self.widget_id} failed to render: {e}")
            return None
