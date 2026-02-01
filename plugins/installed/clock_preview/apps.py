"""
Django app config for Clock Preview plugin.
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class ClockPreviewConfig(AppConfig):
    """Configuration for Clock Preview plugin"""

    name = 'clock_preview'
    verbose_name = 'Analog Clock Preview Plugin'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """
        Called when plugin is activated.
        Registers the clock preview provider and dashboard widget with the hook system.
        """
        logger.info("Initializing Clock Preview Plugin")

        try:
            from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER, UI_DASHBOARD_WIDGET
            from clock_preview.handlers import ClockPreviewProvider
            from clock_preview.widget import ClockWidgetProvider

            # Register the handler for .clock files
            hook_registry.register(
                FILE_PREVIEW_PROVIDER,
                ClockPreviewProvider,
                priority=10,
                mime_type='application/clock'
            )

            # Register the dashboard widget
            hook_registry.register(
                UI_DASHBOARD_WIDGET,
                ClockWidgetProvider,
                priority=5,
            )

            logger.info("Clock Preview Provider and Widget registered")

        except Exception as e:
            logger.error(f"Failed to initialize Clock Preview Plugin: {e}")
            raise
