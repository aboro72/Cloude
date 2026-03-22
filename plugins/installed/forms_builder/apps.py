from django.apps import AppConfig


class FormsBuilderConfig(AppConfig):
    name = 'forms_builder'
    verbose_name = 'Forms Builder Plugin'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from forms_builder.providers import FormsMenuProvider, FormsPageProvider
        from plugins.hooks import UI_APP_PAGE, UI_MENU_ITEM, hook_registry

        hook_registry.register(UI_MENU_ITEM, FormsMenuProvider, priority=60)
        hook_registry.register(UI_APP_PAGE, FormsPageProvider, priority=60, slug='forms')
