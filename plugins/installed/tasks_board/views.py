import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from tasks_board.models import Task, TaskBoard


def _board_access(board, user):
    """Prüft ob User das Board sehen/bearbeiten darf."""
    if board.owner == user:
        return True
    if board.team_site and board.team_site.members.filter(pk=user.pk).exists():
        return True
    return False


@login_required
def board_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip() or 'Neues Board'
        color = request.POST.get('color', '#667eea')
        board = TaskBoard.objects.create(owner=request.user, title=title, color=color)
        return redirect('tasks_board:board_detail', board_id=board.pk)
    return render(request, 'tasks_board/board_create.html', {})


@login_required
def board_detail(request, board_id):
    board = get_object_or_404(TaskBoard, pk=board_id)
    if not _board_access(board, request.user):
        raise Http404

    columns = {
        'todo': {'label': 'Offen', 'icon': 'bi-circle', 'color': '#6c757d'},
        'in_progress': {'label': 'In Bearbeitung', 'icon': 'bi-arrow-repeat', 'color': '#0d6efd'},
        'blocked': {'label': 'Blockiert', 'icon': 'bi-exclamation-triangle', 'color': '#dc3545'},
        'done': {'label': 'Erledigt', 'icon': 'bi-check-circle', 'color': '#198754'},
    }

    tasks_by_status = {}
    for status in columns:
        tasks_by_status[status] = list(
            board.tasks.filter(status=status).select_related('assigned_to').order_by('order', 'created_at')
        )

    from django.contrib.auth.models import User
    all_users = User.objects.filter(is_active=True).only('id', 'username', 'first_name', 'last_name')

    return render(request, 'tasks_board/board.html', {
        'board': board,
        'columns': columns,
        'tasks_by_status': tasks_by_status,
        'all_users': all_users,
    })


@login_required
@require_POST
def board_delete(request, board_id):
    board = get_object_or_404(TaskBoard, pk=board_id, owner=request.user)
    board.delete()
    return redirect('/core/apps/tasks/')


@login_required
@require_POST
def task_add(request, board_id):
    board = get_object_or_404(TaskBoard, pk=board_id)
    if not _board_access(board, request.user):
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)

    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({'error': 'Titel fehlt'}, status=400)

    status = request.POST.get('status', 'todo')
    if status not in ('todo', 'in_progress', 'blocked', 'done'):
        status = 'todo'

    max_order = Task.objects.filter(board=board, status=status).count()
    task = Task.objects.create(
        board=board,
        title=title,
        description=request.POST.get('description', ''),
        status=status,
        priority=request.POST.get('priority', 'normal'),
        due_date=request.POST.get('due_date') or None,
        created_by=request.user,
        order=max_order,
    )
    assigned_id = request.POST.get('assigned_to')
    if assigned_id:
        from django.contrib.auth.models import User
        task.assigned_to = User.objects.filter(pk=assigned_id).first()
        task.save(update_fields=['assigned_to'])

    return JsonResponse({
        'id': task.pk,
        'title': task.title,
        'status': task.status,
        'priority': task.priority,
        'due_date': str(task.due_date) if task.due_date else '',
        'assigned_name': task.assigned_to.get_full_name() or task.assigned_to.username if task.assigned_to else '',
    })


@login_required
@require_POST
def task_move(request, task_id):
    """Drag-Drop: Status wechseln."""
    task = get_object_or_404(Task, pk=task_id)
    if not _board_access(task.board, request.user):
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)

    data = json.loads(request.body)
    new_status = data.get('status')
    if new_status not in ('todo', 'in_progress', 'blocked', 'done'):
        return JsonResponse({'error': 'Ungültiger Status'}, status=400)

    task.status = new_status
    task.order = data.get('order', 0)
    task.save(update_fields=['status', 'order'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def task_update(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if not _board_access(task.board, request.user):
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)

    task.title = request.POST.get('title', task.title).strip() or task.title
    task.description = request.POST.get('description', task.description)
    task.priority = request.POST.get('priority', task.priority)
    task.due_date = request.POST.get('due_date') or None
    assigned_id = request.POST.get('assigned_to')
    if assigned_id:
        from django.contrib.auth.models import User
        task.assigned_to = User.objects.filter(pk=assigned_id).first()
    elif assigned_id == '':
        task.assigned_to = None
    task.save()
    return JsonResponse({'ok': True, 'title': task.title})


@login_required
@require_POST
def task_delete(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if not _board_access(task.board, request.user):
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)
    task.delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def task_reorder(request, task_id):
    """Nach Drag-Drop: Reihenfolge innerhalb einer Spalte neu setzen."""
    task = get_object_or_404(Task, pk=task_id)
    if not _board_access(task.board, request.user):
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)
    data = json.loads(request.body)
    task.order = data.get('order', 0)
    task.save(update_fields=['order'])
    return JsonResponse({'ok': True})
