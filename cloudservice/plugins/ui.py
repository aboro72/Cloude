from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from django.urls import reverse


class PluginMenuItemProvider(ABC):
    menu_label: str = ""
    menu_icon: str = "bi-grid"
    menu_order: int = 100

    @abstractmethod
    def get_url(self) -> str:
        pass

    def is_visible(self, request) -> bool:
        return True

    def render(self, request) -> Optional[Dict[str, Any]]:
        if not self.is_visible(request):
            return None

        return {
            'label': self.menu_label,
            'icon': self.menu_icon,
            'url': self.get_url(),
            'order': self.menu_order,
        }


class PluginPageProvider(ABC):
    page_slug: str = ""
    page_title: str = ""
    page_icon: str = "bi-grid"

    @abstractmethod
    def get_template_name(self) -> str:
        pass

    @abstractmethod
    def get_context(self, request) -> Dict[str, Any]:
        pass

    def is_visible(self, request) -> bool:
        return True

    def get_url(self) -> str:
        return reverse('core:plugin_app', kwargs={'slug': self.page_slug})

    def render(self, request) -> Dict[str, Any]:
        context = self.get_context(request)
        context.setdefault('page_title', self.page_title)
        context.setdefault('page_icon', self.page_icon)
        context.setdefault('page_slug', self.page_slug)
        return context
