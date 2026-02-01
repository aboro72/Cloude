"""
Django app config for RSS Feed plugin.
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class RssFeedConfig(AppConfig):
    """Configuration for RSS Feed plugin"""

    name = 'rss_feed'
    verbose_name = 'Heise RSS Feed Plugin'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """
        Called when plugin is activated.
        Registers the RSS feed widget with the hook system.
        """
        logger.info("Initializing Heise RSS Feed Plugin")

        try:
            from plugins.hooks import hook_registry, UI_DASHBOARD_WIDGET
            from rss_feed.widget import RssFeedWidgetProvider

            # Register the dashboard widget
            hook_registry.register(
                UI_DASHBOARD_WIDGET,
                RssFeedWidgetProvider,
                priority=25,
            )

            logger.info("RSS Feed Widget registered successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RSS Feed Plugin: {e}")
            raise
