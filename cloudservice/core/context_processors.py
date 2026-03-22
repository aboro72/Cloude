from plugins.hooks import UI_MENU_ITEM, hook_registry
from plugins.status import is_plugin_enabled


def plugin_menu_items(request):
    items = []

    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'plugin_menu_items': items}

    for handler in hook_registry.get_handlers(UI_MENU_ITEM):
        try:
            provider = handler()
            rendered = provider.render(request)
            if rendered:
                items.append(rendered)
        except Exception:
            continue

    items.sort(key=lambda item: item.get('order', 100))
    return {
        'plugin_menu_items': items,
        'mysite_enabled': is_plugin_enabled('mysite-hub'),
    }
