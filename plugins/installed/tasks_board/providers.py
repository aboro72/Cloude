from django.template.loader import render_to_string


class TasksMenuProvider:
    label = 'Aufgaben'
    icon = 'bi-kanban'
    url = '/core/apps/tasks/'
    priority = 50


class TasksPageProvider:
    slug = 'tasks'
    title = 'Aufgaben'

    def render(self, request):
        from tasks_board.views import board_overview
        ctx = board_overview(request)
        ctx['request'] = request
        return render_to_string('tasks_board/overview.html', ctx)
