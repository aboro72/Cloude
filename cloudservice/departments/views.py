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


# â”€â”€ Permission helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _require_manage(request, dept):
    """Returns a 403 response or None if access is granted."""
    if dept.user_can_manage(request.user):
        return None
    return render(request, '403.html', {
        'error_message': f'Du hast keine Berechtigung, die Abteilung â€ž{dept.name}" zu verwalten.',
        'back_url': reverse_lazy('departments:detail', kwargs={'slug': dept.slug}),
        'back_label': f'ZurÃ¼ck zu {dept.name}',
    }, status=403)
def _sync_department_leaders_to_team_site(dept, site):
    """
    Ensure department head/managers can access/manage the Team-Site.

    - Adds department head + dept membership roles (manager/head) as `members`
      so they can open the Team-Site detail page.
    - Adds the same set as `team_leaders` so they can manage settings/news.

    Intentionally does not remove existing members/leaders.
    """
    leader_ids = set(
        dept.memberships
        .filter(role__in=['manager', 'head'])
        .values_list('user_id', flat=True)
    )
    if dept.head_id:
        leader_ids.add(dept.head_id)

    if not leader_ids:
        return

    preexisting_member_ids = set(site.members.filter(id__in=leader_ids).values_list('id', flat=True))
    preexisting_leader_ids = set(site.team_leaders.filter(id__in=leader_ids).values_list('id', flat=True))

    to_add_members = leader_ids - preexisting_member_ids
    to_add_leaders = leader_ids - preexisting_leader_ids

    if to_add_members:
        site.members.add(*to_add_members)
    if to_add_leaders:
        site.team_leaders.add(*to_add_leaders)

    try:
        from sharing.models import GroupShareDepartmentAutoRole
    except Exception:
        return

    for user_id in leader_ids:
        added_to_members = user_id in to_add_members
        added_to_team_leaders = user_id in to_add_leaders
        if not (added_to_members or added_to_team_leaders):
            continue
        GroupShareDepartmentAutoRole.objects.update_or_create(
            group=site,
            department=dept,
            user_id=user_id,
            defaults={
                'preexisting_member': user_id in preexisting_member_ids,
                'preexisting_team_leader': user_id in preexisting_leader_ids,
                'added_to_members': added_to_members,
                'added_to_team_leaders': added_to_team_leaders,
            },
        )

# â”€â”€ List â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


# â”€â”€ Detail â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
        manageable_sites = [site for site in team_sites if site.user_can_manage(user)]

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
            'manageable_sites': manageable_sites,
            'news': news,
            'can_manage': can_manage,
            'is_member': is_member,
            'can_create_team_site': can_manage,
            'all_users': (
                User.objects.filter(is_active=True).order_by('last_name', 'username')
                if can_manage else None
            ),
            'role_choices': DepartmentMembership.ROLE_CHOICES,
        })
        return ctx


# â”€â”€ Create / Edit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
        ctx['page_title'] = f'â€ž{self.object.name}" bearbeiten'
        ctx['all_users'] = User.objects.filter(is_active=True).order_by('last_name', 'username')
        ctx['icons'] = _icon_choices()
        return ctx


# â”€â”€ Delete â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class DepartmentDeleteView(LoginRequiredMixin, View):
    def post(self, request, slug):
        if not request.user.has_perm('departments.manage_any_department'):
            return render(request, '403.html', {
                'error_message': 'Du hast keine Berechtigung, Abteilungen zu lÃ¶schen.',
            }, status=403)
        dept = get_object_or_404(Department, slug=slug)
        dept.delete()
        return redirect('departments:list')


# â”€â”€ AJAX: Member management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class DepartmentMemberAddView(LoginRequiredMixin, View):
    def post(self, request, slug):
        dept = get_object_or_404(Department, slug=slug)
        denied = _require_manage(request, dept)
        if denied:
            return JsonResponse({'error': 'Kein Zugriff'}, status=403)

        try:
            data = json.loads(request.body)
        except ValueError:
            return JsonResponse({'error': 'UngÃ¼ltige Daten'}, status=400)

        user_id = data.get('user_id')
        role = data.get('role', 'member')
        if role not in dict(DepartmentMembership.ROLE_CHOICES):
            return JsonResponse({'error': 'UngÃ¼ltige Rolle'}, status=400)

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
            return JsonResponse({'error': 'UngÃ¼ltige Daten'}, status=400)

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
            return JsonResponse({'error': 'UngÃ¼ltige Daten'}, status=400)

        role = data.get('role')
        if role not in dict(DepartmentMembership.ROLE_CHOICES):
            return JsonResponse({'error': 'UngÃ¼ltige Rolle'}, status=400)

        updated = DepartmentMembership.objects.filter(
            department=dept, user_id=data.get('user_id'),
        ).update(role=role)
        if not updated:
            return JsonResponse({'error': 'Mitgliedschaft nicht gefunden'}, status=404)
        return JsonResponse({'ok': True, 'role': role})


# â”€â”€ Site assignment â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
            return JsonResponse({'error': 'UngÃ¼ltige Daten'}, status=400)

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
            _sync_department_leaders_to_team_site(dept, site)
        elif action == 'unassign':
            if site.department_id == dept.pk:
                try:
                    from sharing.models import GroupShareDepartmentAutoRole
                    auto_roles = list(GroupShareDepartmentAutoRole.objects.filter(group=site, department=dept))
                except Exception:
                    auto_roles = []

                if auto_roles:
                    remove_member_ids = [
                        r.user_id for r in auto_roles
                        if r.added_to_members and not r.preexisting_member
                    ]
                    remove_leader_ids = [
                        r.user_id for r in auto_roles
                        if r.added_to_team_leaders and not r.preexisting_team_leader
                    ]

                    if remove_leader_ids:
                        site.team_leaders.remove(*remove_leader_ids)
                    if remove_member_ids:
                        site.members.remove(*remove_member_ids)

                    try:
                        GroupShareDepartmentAutoRole.objects.filter(group=site, department=dept).delete()
                    except Exception:
                        pass

                site.department = None
                site.save(update_fields=['department'])
        else:
            return JsonResponse({'error': 'UngÃ¼ltige Aktion'}, status=400)

        return JsonResponse({'ok': True, 'action': action, 'site_id': site_id, 'site_name': site.group_name})


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _icon_choices():
    return [
        ('bi-building', 'GebÃ¤ude'),
        ('bi-building-fill', 'GebÃ¤ude (gefÃ¼llt)'),
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

