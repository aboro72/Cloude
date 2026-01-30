"""
Plugin hook system for extensibility.

Central registry where plugins can register handlers for extension points.
Supports multiple handlers per hook with priority-based execution.
"""

from typing import Callable, List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class HookRegistry:
    """
    Central registry for plugin hooks.

    Uses singleton pattern to ensure single global registry.
    Supports registering, retrieving, and executing handlers for hooks.
    """

    _instance = None
    _hooks: Dict[str, List[Dict[str, Any]]] = {}

    def __new__(cls):
        """Ensure singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._hooks = {}
        return cls._instance

    def register(self, hook_name: str, handler: Callable,
                 priority: int = 10, **metadata):
        """
        Register a hook handler.

        Args:
            hook_name: Name of the hook (e.g., 'file_preview_provider')
            handler: Callable that handles this hook
            priority: Lower number = higher priority (default 10)
            **metadata: Additional metadata for filtering (e.g., mime_type='text/markdown')
        """
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []

        self._hooks[hook_name].append({
            'handler': handler,
            'priority': priority,
            'metadata': metadata,
        })

        # Sort by priority (lower = higher priority)
        self._hooks[hook_name].sort(key=lambda x: x['priority'])

        logger.debug(f"Registered hook: {hook_name} with handler {handler.__name__} (priority={priority})")

    def unregister(self, hook_name: str, handler: Callable):
        """
        Unregister a specific hook handler.

        Args:
            hook_name: Name of the hook
            handler: Handler to unregister
        """
        if hook_name in self._hooks:
            before = len(self._hooks[hook_name])
            self._hooks[hook_name] = [
                h for h in self._hooks[hook_name]
                if h['handler'] != handler
            ]
            after = len(self._hooks[hook_name])
            if before > after:
                logger.debug(f"Unregistered hook: {hook_name}")

    def clear_plugin_hooks(self, plugin_module: str):
        """
        Clear all hooks registered by a specific plugin.

        Args:
            plugin_module: Module prefix (e.g., 'plugins.installed.markdown_preview')
        """
        removed_count = 0
        for hook_name in list(self._hooks.keys()):
            before = len(self._hooks[hook_name])
            self._hooks[hook_name] = [
                h for h in self._hooks[hook_name]
                if not h['handler'].__module__.startswith(plugin_module)
            ]
            after = len(self._hooks[hook_name])
            removed_count += (before - after)

        logger.info(f"Cleared {removed_count} hooks for plugin module: {plugin_module}")

    def get_handlers(self, hook_name: str, **filters) -> List[Callable]:
        """
        Get handlers for a hook, optionally filtered by metadata.

        Args:
            hook_name: Name of the hook
            **filters: Metadata filters (e.g., mime_type='text/markdown')

        Returns:
            List of handlers sorted by priority
        """
        if hook_name not in self._hooks:
            return []

        handlers = []
        for hook_info in self._hooks[hook_name]:
            # Filter by metadata if provided
            if filters:
                match = all(
                    hook_info['metadata'].get(k) == v
                    for k, v in filters.items()
                )
                if not match:
                    continue

            handlers.append(hook_info['handler'])

        return handlers

    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """
        Execute all handlers for a hook.

        Args:
            hook_name: Name of the hook
            *args: Positional arguments to pass to handlers
            **kwargs: Keyword arguments to pass to handlers

        Returns:
            List of return values from each handler
        """
        results = []
        handlers = self.get_handlers(hook_name)

        if not handlers:
            logger.debug(f"No handlers registered for hook: {hook_name}")
            return results

        for handler in handlers:
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook {hook_name} handler {handler.__name__} failed: {e}")

        return results

    def get_providers(self, hook_name: str, **filters) -> List[Any]:
        """
        Get provider instances for a hook (for factory patterns).

        Instantiates handlers and returns instances.

        Args:
            hook_name: Name of the hook
            **filters: Metadata filters

        Returns:
            List of instantiated provider objects
        """
        providers = []
        handlers = self.get_handlers(hook_name, **filters)

        for handler in handlers:
            try:
                provider = handler()
                providers.append(provider)
            except Exception as e:
                logger.error(f"Failed to instantiate provider {handler.__name__}: {e}")

        return providers


# Global singleton instance
hook_registry = HookRegistry()


def register_hook(hook_name: str, priority: int = 10, **metadata):
    """
    Decorator for registering hook handlers.

    Usage:
        @register_hook('file_preview_provider', priority=10, mime_type='text/markdown')
        def my_preview_handler():
            pass

    Args:
        hook_name: Name of the hook
        priority: Lower = higher priority
        **metadata: Metadata for filtering
    """
    def decorator(func: Callable) -> Callable:
        hook_registry.register(hook_name, func, priority, **metadata)
        return func

    return decorator


# ============================================================================
# Built-in Hook Definitions
# ============================================================================

# File preview hooks
FILE_PREVIEW_PROVIDER = 'file_preview_provider'
"""
Hook for file preview providers.

Handler should be a callable that returns an instance of FilePreviewProvider.
Metadata: mime_type (string or list of MIME types supported)
"""

# Future hook types (for post-MVP phases)
STORAGE_BACKEND_PROVIDER = 'storage_backend_provider'
FILE_UPLOAD_PREPROCESS = 'file_upload_preprocess'
FILE_UPLOAD_POSTPROCESS = 'file_upload_postprocess'

UI_DASHBOARD_WIDGET = 'ui_dashboard_widget'
UI_FILE_ACTION_BUTTON = 'ui_file_action_button'
UI_MENU_ITEM = 'ui_menu_item'

API_ENDPOINT_PROVIDER = 'api_endpoint_provider'
API_SERIALIZER_EXTEND = 'api_serializer_extend'

WORKFLOW_STEP_PROVIDER = 'workflow_step_provider'
WORKFLOW_TRIGGER = 'workflow_trigger'

# Event hooks
STORAGE_FILE_UPLOADED = 'storage_file_uploaded'
STORAGE_FILE_DELETED = 'storage_file_deleted'
USER_LOGIN = 'user_login'
