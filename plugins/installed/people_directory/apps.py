from django.apps import AppConfig


class PeopleDirectoryConfig(AppConfig):
    name = 'people_directory'
    verbose_name = 'People Directory Plugin'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from people_directory.providers import PeopleMenuProvider, PeoplePageProvider
        from plugins.hooks import UI_APP_PAGE, UI_MENU_ITEM, hook_registry

        hook_registry.register(UI_MENU_ITEM, PeopleMenuProvider, priority=40)
        hook_registry.register(UI_APP_PAGE, PeoplePageProvider, priority=40, slug='people')
