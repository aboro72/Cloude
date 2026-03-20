from django.apps import AppConfig


class DepartmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'departments'
    verbose_name = 'Abteilungen'

    def ready(self):
        from plugins.hooks import hook_registry, UI_MENU_ITEM
        from departments.providers import DepartmentMenuProvider
        hook_registry.register(UI_MENU_ITEM, DepartmentMenuProvider, priority=25)
