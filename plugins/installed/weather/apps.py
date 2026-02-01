"""
Django app config for Weather Widget plugin.
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class WeatherConfig(AppConfig):
    """Configuration for Weather Widget plugin"""

    name = 'weather'
    verbose_name = 'Weather Widget Plugin'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """
        Called when plugin is activated.
        Registers the weather widget with the hook system.
        """
        logger.info("Initializing Weather Widget Plugin")

        try:
            from plugins.hooks import hook_registry, UI_DASHBOARD_WIDGET
            from weather.widget import WeatherWidgetProvider

            # Register the dashboard widget
            hook_registry.register(
                UI_DASHBOARD_WIDGET,
                WeatherWidgetProvider,
                priority=15,
            )

            logger.info("Weather Widget registered successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Weather Widget Plugin: {e}")
            raise
