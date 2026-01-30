"""
Plugin app configuration.

Handles plugin system initialization and loading of enabled plugins on startup.
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

        Loads all enabled plugins from the database.
        """
        logger.info("Initializing Plugin System")

        try:
            from plugins.loader import PluginLoader

            loader = PluginLoader()
            loader.load_all_enabled()
            logger.info("Plugin System initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing Plugin System: {e}")
