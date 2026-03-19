from django.apps import AppConfig


class LandingEditorConfig(AppConfig):
    name = 'landing_editor'
    verbose_name = 'Landing Page Editor'

    def ready(self):
        from plugins.hooks import hook_registry, UI_MENU_ITEM, UI_APP_PAGE
        from landing_editor.providers import LandingEditorMenuProvider, LandingEditorPageProvider

        hook_registry.register(UI_MENU_ITEM, LandingEditorMenuProvider, priority=90)
        hook_registry.register(UI_APP_PAGE, LandingEditorPageProvider, priority=90, slug='landing-editor')
