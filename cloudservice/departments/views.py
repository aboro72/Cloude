import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from departments.models import Department, DepartmentMembership


# ── Permission helper ─────────────────────────────────────────────────────────

def _require_manage(request, dept):
    """Returns a 403 response or None if access is granted."""
    if dept.user_can_manage(request.user):
        return None
    return render(request, '403.html', {
        'error_message': f'Du hast keine Berechtigung, die Abteilung „{dept.name}" zu verwalten.',
        'back_url': reverse_lazy('departments:detail', kwargs={'slug': dept.slug}),
        'back_label': f'Zurück zu {dept.name}',
    }, status=403)


# ── List ──────────────────────────────────────────────────────────────────────

class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'departments/list.html'
    context_object_name = 'departments'

    def get_queryset(self):
        return Department.objects.select_related('head').prefetch_related('memberships', 'team_sites')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['can_create'] = self.request.user.has_perm('departments.create_department')
        return ctx


# ── Detail ────────────────────────────────────────────────────────────────────

class DepartmentDetailView(LoginRequiredMixin, DetailView):
    model = Department
    template_name = 'departments/detail.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dept = self.object
        user = self.request.user

        memberships = dept.memberships.select_related('user').order_by('role', 'user__last_name')
        team_sites = dept.team_sites.select_related('owner').all()

        from sharing.models import TeamSiteNews
        news = (
            TeamSiteNews.objects
            .filter(group__in=team_sites, is_published=True)
            .select_related('author', 'group')
            .order_by('-created_at')[:10]
        )

        can_manage = dept.user_can_manage(user)
        is_member = dept.memberships.filter(user=user).exists() or dept.head == user

        ctx.update({
            'memberships': memberships,
            'heads': memberships.filter(role='head'),
            'managers': memberships.filter(role='manager'),
            'members': memberships.filter(role='member'),
            'team_sites': team_sites,
            'news': news,
            'can_manage': can_manage,
            'is_member': is_member,
            'all_users': (
                User.objects.filter(is_active=True).order_by('last_name', 'username')
                if can_manage else None
            ),
            'role_choices': DepartmentMembership.ROLE_CHOICES,
        })
        return ctx


# ── Create / Edit ─────────────────────────────────────────────────────────────

class DepartmentCreateView(LoginRequiredMixin, CreateView):
    model = Department
    template_name = 'departments/create_edit.html'
    fields = ['name', 'description', 'icon', 'color', 'head']

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('departments.create_department'):
            return render(request, '403.html', {
                'error_message': 'Du hast keine Berechtigung, Abteilungen zu erstellen.',
            }, status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.slug = slugify(form.instance.name)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('departments:detail', kwargs={'slug': self.object.slug})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Neue Abteilung erstellen'
        ctx['all_users'] = User.objects.filter(is_active=True).order_by('last_name', 'username')
        ctx['icons'] = _icon_choices()
        return ctx


class DepartmentEditView(LoginRequiredMixin, UpdateView):
    model = Department
    template_name = 'departments/create_edit.html'
    fields = ['name', 'description', 'icon', 'color', 'head']
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def dispatch(self, request, *args, **kwargs):
        dept = self.get_object()
        denied = _require_manage(request, dept)
        if denied:
            return denied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        old = Department.objects.get(pk=form.instance.pk)
        if form.instance.name != old.name:
            form.instance.slug = slugify(form.instance.name)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('departments:detail', kwargs={'slug': self.object.slug})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'„{self.object.name}" bearbeiten'
        ctx['all_users'] = User.objects.filter(is_active=True).order_by('last_name', 'username')
        ctx['icons'] = _icon_choices()
        return ctx


# ── Delete ────────────────────────────────────────────────────────────────────

class DepartmentDeleteView(LoginRequiredMixin, View):
    def post(self, request, slug):
        if not request.user.has_perm('departments.manage_any_department'):
            return render(request, '403.html', {
                'error_message': 'Du hast keine Berechtigung, Abteilungen zu löschen.',
            }, status=403)
        dept = get_object_or_404(Department, slug=slug)
        dept.delete()
        return redirect('departments:list')


# ── AJAX: Member management ───────────────────────────────────────────────────

class DepartmentMemberAddView(LoginRequiredMixin, View):
    def post(self, request, slug):
        dept = get_object_or_404(Department, slug=slug)
        denied = _require_manage(request, dept)
        if denied:
            return JsonResponse({'error': 'Kein Zugriff'}, status=403)

        try:
            data = json.loads(request.body)
        except ValueError:
            return JsonResponse({'error': 'Ungültige Daten'}, status=400)

        user_id = data.get('user_id')
        role = data.get('role', 'member')
        if role not in dict(DepartmentMembership.ROLE_CHOICES):
            return JsonResponse({'error': 'Ungültige Rolle'}, status=400)

        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Nutzer nicht gefunden'}, status=404)

        membership, created = DepartmentMembership.objects.get_or_create(
            department=dept, user=user, defaults={'role': role},
        )
        if not created:
            membership.role = role
            membership.save()

        return JsonResponse({
            'ok': True,
            'user_id': user.pk,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'role': membership.role,
            'role_label': membership.get_role_display(),
            'created': created,
        })


class DepartmentMemberRemoveView(LoginRequiredMixin, View):
    def post(self, request, slug):
        dept = get_object_or_404(Department, slug=slug)
        denied = _require_manage(request, dept)
        if denied:
            return JsonResponse({'error': 'Kein Zugriff'}, status=403)

        try:
            data = json.loads(request.body)
        except ValueError:
            return JsonResponse({'error': 'Ungültige Daten'}, status=400)

        DepartmentMembership.objects.filter(department=dept, user_id=data.get('user_id')).delete()
        return JsonResponse({'ok': True})


class DepartmentMemberRoleView(LoginRequiredMixin, View):
    def post(self, request, slug):
        dept = get_object_or_404(Department, slug=slug)
        denied = _require_manage(request, dept)
        if denied:
            return JsonResponse({'error': 'Kein Zugriff'}, status=403)

        try:
            data = json.loads(request.body)
        except ValueError:
            return JsonResponse({'error': 'Ungültige Daten'}, status=400)

        role = data.get('role')
        if role not in dict(DepartmentMembership.ROLE_CHOICES):
            return JsonResponse({'error': 'Ungültige Rolle'}, status=400)

        updated = DepartmentMembership.objects.filter(
            department=dept, user_id=data.get('user_id'),
        ).update(role=role)
        if not updated:
            return JsonResponse({'error': 'Mitgliedschaft nicht gefunden'}, status=404)
        return JsonResponse({'ok': True, 'role': role})


# ── Site assignment ───────────────────────────────────────────────────────────

class DepartmentSiteAssignView(LoginRequiredMixin, View):
    def get(self, request, slug):
        dept = get_object_or_404(Department, slug=slug)
        denied = _require_manage(request, dept)
        if denied:
            return denied

        from sharing.models import GroupShare
        assigned = GroupShare.objects.filter(department=dept, is_active=True).select_related('owner')
        unassigned = GroupShare.objects.filter(department__isnull=True, is_active=True).select_related('owner')
        return render(request, 'departments/assign_sites.html', {
            'dept': dept,
            'assigned': assigned,
            'unassigned': unassigned,
        })

    def post(self, request, slug):
        dept = get_object_or_404(Department, slug=slug)
        denied = _require_manage(request, dept)
        if denied:
            return JsonResponse({'error': 'Kein Zugriff'}, status=403)

        try:
            data = json.loads(request.body)
        except ValueError:
            return JsonResponse({'error': 'Ungültige Daten'}, status=400)

        action = data.get('action')
        site_id = data.get('site_id')

        from sharing.models import GroupShare
        try:
            site = GroupShare.objects.get(pk=site_id, is_active=True)
        except GroupShare.DoesNotExist:
            return JsonResponse({'error': 'Team-Site nicht gefunden'}, status=404)

        if action == 'assign':
            site.department = dept
            site.save(update_fields=['department'])
        elif action == 'unassign':
            if site.department_id == dept.pk:
                site.department = None
                site.save(update_fields=['department'])
        else:
            return JsonResponse({'error': 'Ungültige Aktion'}, status=400)

        return JsonResponse({'ok': True, 'action': action, 'site_id': site_id, 'site_name': site.group_name})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _icon_choices():
    return [
        ('bi-building', 'Gebäude'),
        ('bi-building-fill', 'Gebäude (gefüllt)'),
        ('bi-bar-chart-line', 'Management/Strategie'),
        ('bi-people-fill', 'Personal/HR'),
        ('bi-cash-stack', 'Finanzen'),
        ('bi-code-square', 'Entwicklung/IT'),
        ('bi-megaphone', 'Marketing'),
        ('bi-cart', 'Vertrieb'),
        ('bi-tools', 'Technik/Operations'),
        ('bi-shield-check', 'Compliance/Legal'),
        ('bi-graph-up', 'Analytics'),
        ('bi-gear', 'Administration'),
        ('bi-heart', 'Customer Success'),
        ('bi-box', 'Produkt'),
        ('bi-globe', 'International'),
        ('bi-cpu', 'Infrastruktur'),
    ]
