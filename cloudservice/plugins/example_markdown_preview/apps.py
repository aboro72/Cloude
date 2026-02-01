"""
Django app config for Markdown Preview plugin.

When this plugin is activated, AppConfig.ready() is called to register
the preview provider with the plugin hook system.
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class MarkdownPreviewConfig(AppConfig):
    """Configuration for Markdown Preview plugin"""

    name = 'markdown_preview'
    verbose_name = 'Markdown File Preview Plugin'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """
        Called when plugin is activated.

        Registers the Markdown preview provider with the hook system.
        """
        logger.info("Initializing Markdown Preview Plugin")

        try:
            from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER
            from markdown_preview.handlers import MarkdownPreviewProvider

            # Register the handler for markdown file types
            hook_registry.register(
                FILE_PREVIEW_PROVIDER,
                MarkdownPreviewProvider,
                priority=10,
                mime_type='text/markdown'
            )

            logger.info("Markdown Preview Provider registered")

        except Exception as e:
            logger.error(f"Failed to initialize Markdown Preview Plugin: {e}")
            raise
