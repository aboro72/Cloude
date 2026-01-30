"""
Plugin app configuration.

Handles plugin system initialization and management.
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class PluginsConfig(AppConfig):
    """Configuration for the plugins app"""

    name = 'plugins'
    verbose_name = 'Plugin System'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """
        Called when the app is ready.

        Note: We don't auto-load plugins on startup to avoid interfering
        with Django's app registry initialization. Plugins are loaded
        on-demand when the admin clicks "Activate".
        """
        logger.info("Plugin System ready (plugins loaded on-demand)")
        # Plugins are not auto-loaded on startup - this prevents
        # "dictionary changed size during iteration" errors during
        # Django initialization. Plugins are loaded when admin activates them.
