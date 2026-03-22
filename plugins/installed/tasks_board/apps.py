from django.apps import AppConfig


class TasksBoardConfig(AppConfig):
    name = 'tasks_board'
    verbose_name = 'Tasks Board Plugin'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from tasks_board.providers import TasksMenuProvider, TasksPageProvider
        from plugins.hooks import UI_APP_PAGE, UI_MENU_ITEM, hook_registry

        hook_registry.register(UI_MENU_ITEM, TasksMenuProvider, priority=50)
        hook_registry.register(UI_APP_PAGE, TasksPageProvider, priority=50, slug='tasks')
