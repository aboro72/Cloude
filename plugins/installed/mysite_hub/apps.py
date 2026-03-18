from django.apps import AppConfig


class MySiteHubConfig(AppConfig):
    name = 'mysite_hub'
    verbose_name = 'MySite Hub Plugin'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from mysite_hub.providers import (
            DepartmentEngineeringPageProvider,
            DepartmentFinancePageProvider,
            DepartmentManagementPageProvider,
            DepartmentPeoplePageProvider,
            MySiteMenuProvider,
            MySitePageProvider,
        )
        from plugins.hooks import UI_APP_PAGE, UI_MENU_ITEM, hook_registry

        hook_registry.register(UI_MENU_ITEM, MySiteMenuProvider, priority=30)
        hook_registry.register(UI_APP_PAGE, MySitePageProvider, priority=30, slug='mysite')
        hook_registry.register(UI_APP_PAGE, DepartmentManagementPageProvider, priority=31, slug='department-management')
        hook_registry.register(UI_APP_PAGE, DepartmentPeoplePageProvider, priority=31, slug='department-people')
        hook_registry.register(UI_APP_PAGE, DepartmentFinancePageProvider, priority=31, slug='department-finance')
        hook_registry.register(UI_APP_PAGE, DepartmentEngineeringPageProvider, priority=31, slug='department-engineering')
