from django.urls import reverse

from plugins.ui import PluginMenuItemProvider


class DepartmentMenuProvider(PluginMenuItemProvider):
    menu_label = 'Abteilungen'
    menu_icon = 'bi-building'
    menu_order = 25

    def get_url(self) -> str:
        return reverse('departments:list')
