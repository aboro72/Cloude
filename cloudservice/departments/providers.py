from django.urls import reverse

from plugins.ui import PluginMenuItemProvider
from plugins.status import is_plugin_enabled


class DepartmentMenuProvider(PluginMenuItemProvider):
    menu_label = 'Abteilungen'
    menu_icon = 'bi-building'
    menu_order = 25

    def get_url(self) -> str:
        return reverse('departments:list')

    def is_visible(self, request) -> bool:
        return request.user.is_authenticated and is_plugin_enabled('mysite-hub')
