import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from tasks_board.models import Task, TaskBoard


# ── Permission helpers ────────────────────────────────────────────────────────

def _dept_membership(board, user):
    """Returns DepartmentMembership or None if user is head/member of board.department."""
    if not board.department_id:
        return None
    dept = board.department
    if dept.head_id == user.pk:
        return 'head'
    try:
        from departments.models import DepartmentMembership
        m = DepartmentMembership.objects.get(department=dept, user=user)
        return m.role  # 'member', 'manager', 'head'
    except Exception:
        return None


def _board_access(board, user):
    """True if user may view the board."""
    if board.owner_id == user.pk:
        return True
    if board.team_site_id and board.team_site.members.filter(pk=user.pk).exists():
        return True
    if board.department_id:
        return _dept_membership(board, user) is not None
    return False


def _can_manage(board, user):
    """True if user may create/edit/delete tasks and assign them to others."""
    if board.owner_id == user.pk:
        return True
    if board.team_site_id and board.team_site.user_can_manage(user):
        return True
    if board.department_id:
        role = _dept_membership(board, user)
        return role in ('manager', 'head')
    return False


def _dept_members(board):
    """Returns active users of board.department (for assignment dropdown)."""
    if not board.department_id:
        return User.objects.none()
    dept = board.department
    from departments.models import DepartmentMembership
    member_ids = list(
        DepartmentMembership.objects.filter(department=dept)
        .values_list('user_id', flat=True)
    )
    if dept.head_id:
        member_ids.append(dept.head_id)
    return User.objects.filter(pk__in=member_ids, is_active=True).order_by('last_name', 'username')


# ── Overview ──────────────────────────────────────────────────────────────────

def board_overview(request):
    """Rendered by PluginPageProvider as the plugin entry page."""
    user = request.user
    personal_boards = TaskBoard.objects.filter(
        owner=user, team_site__isnull=True, department__isnull=True
    ).prefetch_related('tasks')
    team_boards = TaskBoard.objects.filter(
        Q(owner=user) | Q(team_site__members=user),
        team_site__isnull=False,
    ).distinct().select_related('team_site').prefetch_related('tasks')

    # Abteilungs-Boards: alle Boards von Abteilungen, in denen der User Mitglied ist
    from departments.models import DepartmentMembership
    dept_ids = list(
        DepartmentMembership.objects.filter(user=user).values_list('department_id', flat=True)
    )
    if user.profile.headed_departments.exists() if hasattr(user, 'profile') else False:
        pass  # handled below
    headed_ids = list(user.headed_departments.values_list('pk', flat=True))
    all_dept_ids = list(set(dept_ids) | set(headed_ids))

    dept_boards = TaskBoard.objects.filter(
        department_id__in=all_dept_ids
    ).select_related('department').prefetch_related('tasks') if all_dept_ids else TaskBoard.objects.none()

    # Departments where user is manager/head → can create dept board
    manageable_depts = []
    if all_dept_ids:
        from departments.models import Department
        manageable_depts = list(
            Department.objects.filter(
                Q(head=user) | Q(memberships__user=user, memberships__role__in=['manager', 'head']),
            ).distinct()
        )

    return {
        'personal_boards': personal_boards,
        'team_boards': team_boards,
        'dept_boards': dept_boards,
        'manageable_depts': manageable_depts,
    }


# ── Board Create ──────────────────────────────────────────────────────────────

@login_required
def board_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip() or 'Neues Board'
        color = request.POST.get('color', '#667eea')
        dept_id = request.POST.get('department') or None

        board = TaskBoard(owner=request.user, title=title, color=color)

        if dept_id:
            from departments.models import Department
            try:
                dept = Department.objects.get(pk=dept_id)
                if dept.user_can_manage(request.user):
                    board.department = dept
            except Department.DoesNotExist:
                pass

        board.save()
        return redirect('tasks_board:board_detail', board_id=board.pk)

    # GET: collect manageable departments for the form
    from departments.models import Department, DepartmentMembership
    from django.db.models import Q as DQ
    manageable_depts = Department.objects.filter(
        DQ(head=request.user) | DQ(memberships__user=request.user, memberships__role__in=['manager', 'head'])
    ).distinct()

    return render(request, 'tasks_board/board_create.html', {
        'manageable_depts': manageable_depts,
    })


# ── Board Detail ──────────────────────────────────────────────────────────────

@login_required
def board_detail(request, board_id):
    board = get_object_or_404(TaskBoard.objects.select_related('department', 'team_site'), pk=board_id)
    if not _board_access(board, request.user):
        raise Http404

    can_manage = _can_manage(board, request.user)

    columns = {
        'todo':        {'label': 'Offen',         'icon': 'bi-circle',               'color': '#6c757d'},
        'in_progress': {'label': 'In Bearbeitung', 'icon': 'bi-arrow-repeat',         'color': '#0d6efd'},
        'blocked':     {'label': 'Blockiert',      'icon': 'bi-exclamation-triangle', 'color': '#dc3545'},
        'done':        {'label': 'Erledigt',        'icon': 'bi-check-circle',         'color': '#198754'},
    }

    tasks_by_status = {}
    for status in columns:
        qs = board.tasks.filter(status=status).select_related('assigned_to').order_by('order', 'created_at')
        # Members only see their own tasks + unassigned tasks
        if not can_manage:
            qs = qs.filter(Q(assigned_to=request.user) | Q(assigned_to__isnull=True))
        tasks_by_status[status] = list(qs)

    # Assignee dropdown: for dept boards, only dept members; otherwise all active users
    if board.is_dept_board:
        all_users = _dept_members(board)
    else:
        all_users = User.objects.filter(is_active=True).only('id', 'username', 'first_name', 'last_name')

    return render(request, 'tasks_board/board.html', {
        'board': board,
        'columns': columns,
        'tasks_by_status': tasks_by_status,
        'all_users': all_users,
        'can_manage': can_manage,
    })


# ── Board Delete ──────────────────────────────────────────────────────────────

@login_required
@require_POST
def board_delete(request, board_id):
    board = get_object_or_404(TaskBoard, pk=board_id)
    if not _can_manage(board, request.user):
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)
    board.delete()
    return redirect('/core/apps/tasks/')


# ── Task Add ──────────────────────────────────────────────────────────────────

@login_required
@require_POST
def task_add(request, board_id):
    board = get_object_or_404(TaskBoard, pk=board_id)
    if not _board_access(board, request.user):
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)

    can_manage = _can_manage(board, request.user)

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
    if assigned_id and can_manage:
        task.assigned_to = User.objects.filter(pk=assigned_id).first()
        task.save(update_fields=['assigned_to'])
    elif not assigned_id and not can_manage:
        # Members self-assign when adding a task
        task.assigned_to = request.user
        task.save(update_fields=['assigned_to'])

    return JsonResponse({
        'id': task.pk,
        'title': task.title,
        'status': task.status,
        'priority': task.priority,
        'due_date': str(task.due_date) if task.due_date else '',
        'assigned_name': task.assigned_to.get_full_name() or task.assigned_to.username if task.assigned_to else '',
        'assigned_to_id': task.assigned_to_id or '',
        'is_mine': task.assigned_to_id == request.user.pk,
        'is_unassigned': task.assigned_to_id is None,
    })


# ── Task Claim (self-assign) ──────────────────────────────────────────────────

@login_required
@require_POST
def task_claim(request, task_id):
    """A department/team member claims an unassigned task."""
    task = get_object_or_404(Task.objects.select_related('board'), pk=task_id)
    if not _board_access(task.board, request.user):
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)
    if task.assigned_to_id is not None:
        return JsonResponse({'error': 'Bereits vergeben'}, status=400)
    task.assigned_to = request.user
    task.save(update_fields=['assigned_to'])
    return JsonResponse({
        'ok': True,
        'assigned_name': request.user.get_full_name() or request.user.username,
    })


# ── Task Move ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def task_move(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if not _board_access(task.board, request.user):
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)
    # Members may only move their own tasks
    if not _can_manage(task.board, request.user) and task.assigned_to_id != request.user.pk:
        return JsonResponse({'error': 'Nur eigene Aufgaben verschieben'}, status=403)

    data = json.loads(request.body)
    new_status = data.get('status')
    if new_status not in ('todo', 'in_progress', 'blocked', 'done'):
        return JsonResponse({'error': 'Ungültiger Status'}, status=400)

    task.status = new_status
    task.order = data.get('order', 0)
    task.save(update_fields=['status', 'order'])
    return JsonResponse({'ok': True})


# ── Task Update ───────────────────────────────────────────────────────────────

@login_required
@require_POST
def task_update(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if not _board_access(task.board, request.user):
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)
    # Members may only edit their own tasks
    if not _can_manage(task.board, request.user) and task.assigned_to_id != request.user.pk:
        return JsonResponse({'error': 'Nur eigene Aufgaben bearbeiten'}, status=403)

    task.title = request.POST.get('title', task.title).strip() or task.title
    task.description = request.POST.get('description', task.description)
    task.priority = request.POST.get('priority', task.priority)
    task.due_date = request.POST.get('due_date') or None

    # Only managers may re-assign
    if _can_manage(task.board, request.user):
        assigned_id = request.POST.get('assigned_to')
        if assigned_id:
            task.assigned_to = User.objects.filter(pk=assigned_id).first()
        elif assigned_id == '':
            task.assigned_to = None

    task.save()
    return JsonResponse({'ok': True, 'title': task.title})


# ── Task Delete ───────────────────────────────────────────────────────────────

@login_required
@require_POST
def task_delete(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if not _can_manage(task.board, request.user):
        return JsonResponse({'error': 'Nur Manager dürfen Aufgaben löschen'}, status=403)
    task.delete()
    return JsonResponse({'ok': True})


# ── Task Reorder ──────────────────────────────────────────────────────────────

@login_required
@require_POST
def task_reorder(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if not _board_access(task.board, request.user):
        return JsonResponse({'error': 'Kein Zugriff'}, status=403)
    data = json.loads(request.body)
    task.order = data.get('order', 0)
    task.save(update_fields=['order'])
    return JsonResponse({'ok': True})
