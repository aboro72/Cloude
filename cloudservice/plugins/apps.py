"""
Plugin app configuration.

Handles plugin system initialization and management.
"""

import sys
import warnings
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
        Discover plugins and register hooks for enabled ones.
        """
        # Skip during migrations or other management commands
        skip_commands = ['migrate', 'makemigrations', 'collectstatic', 'check']
        if any(cmd in sys.argv for cmd in skip_commands):
            logger.debug("Plugin System: Skipping during management command")
            return

        logger.info("Plugin System initializing...")

        try:
            from plugins.loader import PluginLoader

            loader = PluginLoader()

            # Suppress the "database access during initialization" warning
            # This is safe because we're only reading plugin metadata
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='.*database during app initialization.*')

                # Step 1: Discover plugins from folders
                loader.discover_plugins()

                # Step 2: Register hooks for enabled plugins
                loader.register_all_enabled_hooks()

            logger.info("Plugin System ready")

        except Exception as e:
            logger.warning(f"Plugin System initialization error: {e}")
