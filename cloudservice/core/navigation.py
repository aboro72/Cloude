from django.urls import reverse

from plugins.hooks import UI_APP_PAGE, hook_registry


DEFAULT_PLUGIN_APP_SLUG = 'mysite'
DEFAULT_STORAGE_URL_NAME = 'storage:file_list'


def get_optional_plugin_app_url(slug, request=None):
    """Return a plugin app URL when the provider is available and visible."""
    handlers = hook_registry.get_handlers(UI_APP_PAGE, slug=slug)

    for handler in handlers:
        try:
            provider = handler()
            if request is not None and not provider.is_visible(request):
                continue
            return provider.get_url()
        except Exception:
            continue

    return None


def get_authenticated_home_url(request=None):
    """Resolve the default post-login start page."""
    plugin_url = get_optional_plugin_app_url(DEFAULT_PLUGIN_APP_SLUG, request=request)
    if plugin_url:
        return plugin_url
    return reverse(DEFAULT_STORAGE_URL_NAME)
