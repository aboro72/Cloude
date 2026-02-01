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
        Registers the clock preview provider with the hook system.
        """
        logger.info("Initializing Clock Preview Plugin")

        try:
            from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER
            from clock_preview.handlers import ClockPreviewProvider

            # Register the handler for .plug files
            hook_registry.register(
                FILE_PREVIEW_PROVIDER,
                ClockPreviewProvider,
                priority=10,
                plugin_type='file_preview',
                mime_type='application/plugin'
            )

            logger.info("Clock Preview Provider registered")

        except Exception as e:
            logger.error(f"Failed to initialize Clock Preview Plugin: {e}")
            raise
