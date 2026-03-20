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
        from tasks_board.models import TaskBoard

        # Persönliche Boards des Users
        personal_boards = TaskBoard.objects.filter(
            owner=request.user, team_site__isnull=True
        )

        # Team-Boards: Boards von Team-Sites, in denen der User Mitglied ist
        team_boards = TaskBoard.objects.filter(
            team_site__members=request.user
        ).select_related('team_site').distinct()

        return render_to_string(
            'tasks_board/overview.html',
            {
                'personal_boards': personal_boards,
                'team_boards': team_boards,
                'request': request,
            },
        )
