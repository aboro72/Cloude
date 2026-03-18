from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CollaboraOnlineConfig(AppConfig):
    name = 'collabora_online'
    verbose_name = 'Collabora Online Plugin'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        logger.info("Initializing Collabora Online Plugin")

        try:
            from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER
            from collabora_online.handlers import CollaboraPreviewProvider

            hook_registry.register(
                FILE_PREVIEW_PROVIDER,
                CollaboraPreviewProvider,
                priority=5,
                mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            )
            logger.info("Collabora Online Preview Provider registered")
        except Exception as e:
            logger.error(f"Failed to initialize Collabora Online Plugin: {e}")
            raise

