from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core'

    def ready(self):
        """Import signals and register built-in widgets when app is ready"""
        import core.signals  # noqa

        # Register built-in dashboard widgets
        self._register_builtin_widgets()

    def _register_builtin_widgets(self):
        """Register built-in widgets with the hook system."""
        try:
            from plugins.hooks import hook_registry, UI_DASHBOARD_WIDGET
            from core.widgets import RecentFilesWidget, StorageStatsWidget

            # Register storage stats widget
            hook_registry.register(
                UI_DASHBOARD_WIDGET,
                StorageStatsWidget,
                priority=10,
            )
            logger.debug("Registered StorageStatsWidget")

            # Register recent files widget
            hook_registry.register(
                UI_DASHBOARD_WIDGET,
                RecentFilesWidget,
                priority=20,
            )
            logger.debug("Registered RecentFilesWidget")

            logger.info("Built-in dashboard widgets registered")

        except Exception as e:
            logger.error(f"Failed to register built-in widgets: {e}")
