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
    company_manage_url = ''
    company_list_url = ''
    company_invite_url = ''
    if getattr(request.user, 'profile', None) and request.user.profile.company:
        company = request.user.profile.company
        if company.user_can_manage(request.user):
            company_manage_url = f'/departments/firmen/{company.slug}/verwaltung/'
            company_invite_url = f'/departments/firmen/{company.slug}/verwaltung/#einladungen'
    if request.user.is_superuser or request.user.has_perm('departments.manage_any_company'):
        company_list_url = '/departments/firmen/'

    return {
        'plugin_menu_items': items,
        'mysite_enabled': is_plugin_enabled('mysite-hub'),
        'company_manage_url': company_manage_url,
        'company_invite_url': company_invite_url,
        'company_list_url': company_list_url,
    }
