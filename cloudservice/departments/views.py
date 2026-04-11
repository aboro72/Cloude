import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from departments.forms import CompanyForm, CompanyInvitationForm
from departments.models import Company, CompanyInvitation, Department, DepartmentMembership


def _user_company(user):
    if not user or not user.is_authenticated or not hasattr(user, 'profile'):
        return None
    return user.profile.company


def _url_company(user, company_slug):
    queryset = Company.objects.filter(slug=company_slug, is_active=True)
    user_company = _user_company(user)
    if user_company and not user.has_perm('departments.manage_any_department'):
        queryset = queryset.filter(pk=user_company.pk)
    return get_object_or_404(queryset)


def _manageable_companies(user):
    queryset = Company.objects.filter(is_active=True).prefetch_related('admins')
    if user.is_superuser or user.has_perm('departments.manage_any_company'):
        return queryset.order_by('name')
    return queryset.filter(pk__in=list(user.managed_companies.values_list('pk', flat=True)) + list(user.owned_companies.values_list('pk', flat=True))).distinct().order_by('name')


def _department_queryset(user):
    queryset = Department.objects.select_related('company', 'head')
    company = _user_company(user)
    if company:
        queryset = queryset.filter(company=company)
    return queryset


def _require_manage(request, dept):
    if dept.user_can_manage(request.user):
        return None
    return render(request, '403.html', {
        'error_message': f'Du hast keine Berechtigung, den Bereich "{dept.name}" zu verwalten.',
        'back_url': reverse_lazy('departments:detail', kwargs={'company_slug': dept.company.slug, 'slug': dept.slug}),
        'back_label': f'Zurueck zu {dept.name}',
    }, status=403)


def _require_company_manage(request, company):
    if company.user_can_manage(request.user):
        return None
    return render(request, '403.html', {
        'error_message': f'Du hast keine Berechtigung, die Firma "{company.name}" zu verwalten.',
        'back_url': reverse_lazy('departments:company_detail', kwargs={'company_slug': company.slug}),
        'back_label': f'Zurueck zu {company.name}',
    }, status=403)


class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'departments/list.html'
    context_object_name = 'departments'

    def get_company(self):
        return _url_company(self.request.user, self.kwargs['company_slug'])

    def get_queryset(self):
        return _department_queryset(self.request.user).filter(company=self.get_company()).prefetch_related('memberships', 'team_sites')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['can_create'] = self.request.user.has_perm('departments.create_department')
        ctx['company'] = self.get_company()
        return ctx


class DepartmentCompanyRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        company = _user_company(request.user)
        if not company:
            return render(request, '403.html', {
                'error_message': 'Dein Nutzer ist noch keiner Firma zugeordnet.',
            }, status=403)
        return redirect('departments:list', company_slug=company.slug)


class CompanyListView(LoginRequiredMixin, ListView):
    model = Company
    template_name = 'departments/companies_list.html'
    context_object_name = 'companies'

    def get_queryset(self):
        return _manageable_companies(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['can_create_company'] = self.request.user.is_superuser or self.request.user.has_perm('departments.create_company')
        return ctx


class CompanyDetailView(LoginRequiredMixin, DetailView):
    model = Company
    template_name = 'departments/company_detail.html'
    slug_field = 'slug'
    slug_url_kwarg = 'company_slug'
    context_object_name = 'company'

    def get_queryset(self):
        return _manageable_companies(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = self.object
        ctx['areas'] = company.departments.select_related('head').order_by('name')
        ctx['teams'] = company.team_sites.select_related('owner', 'department').order_by('group_name')[:10]
        ctx['employees'] = company.user_profiles.select_related('user', 'department_ref').order_by(
            'user__last_name', 'user__username'
        )[:25]
        ctx['can_manage_company'] = company.user_can_manage(self.request.user)
        ctx['invite_form'] = CompanyInvitationForm(company=company)
        ctx['invites'] = company.invitations.select_related('department', 'invited_by', 'accepted_by').order_by('-created_at')[:20]
        ctx['company_invite_url'] = f"{reverse_lazy('accounts:register')}?invite="
        ctx['owner_name'] = (
            f"{company.owner.get_full_name() or company.owner.username}"
            if company.owner else 'Nicht gesetzt'
        )
        return ctx


class CompanyCreateView(LoginRequiredMixin, CreateView):
    model = Company
    form_class = CompanyForm
    template_name = 'departments/company_form.html'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.has_perm('departments.create_company')):
            return render(request, '403.html', {
                'error_message': 'Du hast keine Berechtigung, Firmen anzulegen.',
            }, status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.owner_id:
            self.object.admins.add(self.object.owner)
        messages.success(self.request, f'Firma "{self.object.name}" wurde erstellt.')
        return response

    def get_success_url(self):
        return reverse_lazy('departments:company_detail', kwargs={'company_slug': self.object.slug})


class CompanyEditView(LoginRequiredMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = 'departments/company_form.html'
    slug_field = 'slug'
    slug_url_kwarg = 'company_slug'

    def get_queryset(self):
        return _manageable_companies(self.request.user)

    def dispatch(self, request, *args, **kwargs):
        company = self.get_object()
        if not company.user_can_manage(request.user):
            return render(request, '403.html', {
                'error_message': f'Du hast keine Berechtigung, die Firma "{company.name}" zu verwalten.',
            }, status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        current_company = self.get_object()
        new_limit = form.cleaned_data['employee_limit']
        current_count = current_company.employee_count
        if new_limit < current_count:
            form.add_error('employee_limit', f'Das Limit darf nicht unter die aktuelle Mitarbeiterzahl von {current_count} fallen.')
            return self.form_invalid(form)

        response = super().form_valid(form)
        if self.object.owner_id:
            self.object.admins.add(self.object.owner)
        messages.success(self.request, f'Firma "{self.object.name}" wurde aktualisiert.')
        return response

    def get_success_url(self):
        return reverse_lazy('departments:company_detail', kwargs={'company_slug': self.object.slug})


class CompanyInvitationCreateView(LoginRequiredMixin, View):
    def post(self, request, company_slug):
        company = get_object_or_404(_manageable_companies(request.user), slug=company_slug)
        denied = _require_company_manage(request, company)
        if denied:
            return denied
        if not company.can_add_employee():
            messages.error(request, f'Die Firma "{company.name}" hat aktuell keine freien Plaetze mehr.')
            return redirect('departments:company_detail', company_slug=company.slug)

        form = CompanyInvitationForm(request.POST, company=company)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.company = company
            invitation.invited_by = request.user
            invitation.save()
            messages.success(request, f'Einladung fuer {invitation.email} wurde erstellt.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        return redirect('departments:company_detail', company_slug=company.slug)


class CompanyInvitationRevokeView(LoginRequiredMixin, View):
    def post(self, request, company_slug, invitation_id):
        company = get_object_or_404(_manageable_companies(request.user), slug=company_slug)
        denied = _require_company_manage(request, company)
        if denied:
            return denied
        invitation = get_object_or_404(company.invitations, pk=invitation_id)
        invitation.is_active = False
        invitation.save(update_fields=['is_active'])
        messages.success(request, f'Einladung fuer {invitation.email} wurde deaktiviert.')
        return redirect('departments:company_detail', company_slug=company.slug)


class DepartmentDetailView(LoginRequiredMixin, DetailView):
    model = Department
    template_name = 'departments/detail.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return _department_queryset(self.request.user).filter(company=self.get_company())

    def get_company(self):
        return _url_company(self.request.user, self.kwargs['company_slug'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dept = self.object
        user = self.request.user

        memberships = dept.memberships.select_related('user').order_by('role', 'user__last_name')
        team_sites = dept.team_sites.select_related('owner', 'company').all()

        from sharing.models import TeamSiteNews
        news = (
            TeamSiteNews.objects
            .filter(group__in=team_sites, is_published=True)
            .select_related('author', 'group')
            .order_by('-created_at')[:10]
        )

        can_manage = dept.user_can_manage(user)
        is_member = dept.memberships.filter(user=user).exists() or dept.head == user

        company_users = User.objects.filter(is_active=True).order_by('last_name', 'username')
        if dept.company_id:
            company_users = company_users.filter(profile__company=dept.company)

        ctx.update({
            'memberships': memberships,
            'heads': memberships.filter(role='head'),
            'managers': memberships.filter(role='manager'),
            'members': memberships.filter(role='member'),
            'team_sites': team_sites,
            'news': news,
            'can_manage': can_manage,
            'is_member': is_member,
            'company': dept.company,
            'all_users': company_users if can_manage else None,
            'role_choices': DepartmentMembership.ROLE_CHOICES,
        })
        return ctx


class DepartmentCreateView(LoginRequiredMixin, CreateView):
    model = Department
    template_name = 'departments/create_edit.html'
    fields = ['company', 'name', 'description', 'icon', 'color', 'head']

    def get_company(self):
        return _url_company(self.request.user, self.kwargs['company_slug'])

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('departments.create_department'):
            return render(request, '403.html', {
                'error_message': 'Du hast keine Berechtigung, Bereiche zu erstellen.',
            }, status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company = self.get_company()
        form.fields['company'].queryset = Company.objects.filter(is_active=True).order_by('name')
        form.fields['company'].queryset = Company.objects.filter(pk=company.pk)
        form.fields['company'].initial = company.pk

        head_queryset = User.objects.filter(is_active=True).order_by('last_name', 'username')
        if company:
            head_queryset = head_queryset.filter(profile__company=company)
        form.fields['head'].queryset = head_queryset
        return form

    def form_valid(self, form):
        form.instance.company = self.get_company()
        form.instance.created_by = self.request.user
        form.instance.slug = slugify(form.instance.name)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('departments:detail', kwargs={'company_slug': self.object.company.slug, 'slug': self.object.slug})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Neuen Bereich erstellen'
        ctx['icons'] = _icon_choices()
        ctx['company'] = self.get_company()
        return ctx


class DepartmentEditView(LoginRequiredMixin, UpdateView):
    model = Department
    template_name = 'departments/create_edit.html'
    fields = ['company', 'name', 'description', 'icon', 'color', 'head']
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return _department_queryset(self.request.user).filter(company=self.get_company())

    def get_company(self):
        return _url_company(self.request.user, self.kwargs['company_slug'])

    def dispatch(self, request, *args, **kwargs):
        dept = self.get_object()
        denied = _require_manage(request, dept)
        if denied:
            return denied
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        viewer_company = self.get_company()
        target_company = self.object.company or viewer_company

        form.fields['company'].queryset = Company.objects.filter(is_active=True).order_by('name')
        if viewer_company and not self.request.user.has_perm('departments.manage_any_department'):
            form.fields['company'].queryset = Company.objects.filter(pk=viewer_company.pk)

        head_queryset = User.objects.filter(is_active=True).order_by('last_name', 'username')
        if target_company:
            head_queryset = head_queryset.filter(profile__company=target_company)
        form.fields['head'].queryset = head_queryset
        return form

    def form_valid(self, form):
        old = Department.objects.get(pk=form.instance.pk)
        if form.instance.name != old.name:
            form.instance.slug = slugify(form.instance.name)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('departments:detail', kwargs={'company_slug': self.object.company.slug, 'slug': self.object.slug})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Bereich "{self.object.name}" bearbeiten'
        ctx['icons'] = _icon_choices()
        ctx['company'] = self.object.company
        return ctx


class DepartmentDeleteView(LoginRequiredMixin, View):
    def post(self, request, company_slug, slug):
        if not request.user.has_perm('departments.manage_any_department'):
            return render(request, '403.html', {
                'error_message': 'Du hast keine Berechtigung, Bereiche zu loeschen.',
            }, status=403)
        dept = get_object_or_404(_department_queryset(request.user).filter(company=_url_company(request.user, self.kwargs['company_slug'])), slug=slug)
        dept.delete()
        return redirect('departments:list', company_slug=dept.company.slug)


class DepartmentMemberAddView(LoginRequiredMixin, View):
    def post(self, request, company_slug, slug):
        dept = get_object_or_404(_department_queryset(request.user).filter(company=_url_company(request.user, self.kwargs['company_slug'])), slug=slug)
        denied = _require_manage(request, dept)
        if denied:
            return JsonResponse({'error': 'Kein Zugriff'}, status=403)

        try:
            data = json.loads(request.body)
        except ValueError:
            return JsonResponse({'error': 'Ungueltige Daten'}, status=400)

        user_id = data.get('user_id')
        role = data.get('role', 'member')
        if role not in dict(DepartmentMembership.ROLE_CHOICES):
            return JsonResponse({'error': 'Ungueltige Rolle'}, status=400)

        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Nutzer nicht gefunden'}, status=404)

        profile = getattr(user, 'profile', None)
        if dept.company_id and profile and profile.company_id != dept.company_id:
            if not dept.company.can_add_employee(exclude_user=user):
                return JsonResponse({
                    'error': f'Die Firma "{dept.company.name}" hat das Limit von {dept.company.employee_limit} Mitarbeitern erreicht.',
                }, status=400)

        if dept.company_id and hasattr(user, 'profile'):
            user.profile.company = dept.company
            user.profile.department_ref = dept
            user.profile.save(update_fields=['company', 'department_ref', 'department'])

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
    def post(self, request, company_slug, slug):
        dept = get_object_or_404(_department_queryset(request.user).filter(company=_url_company(request.user, self.kwargs['company_slug'])), slug=slug)
        denied = _require_manage(request, dept)
        if denied:
            return JsonResponse({'error': 'Kein Zugriff'}, status=403)

        try:
            data = json.loads(request.body)
        except ValueError:
            return JsonResponse({'error': 'Ungueltige Daten'}, status=400)

        DepartmentMembership.objects.filter(department=dept, user_id=data.get('user_id')).delete()
        return JsonResponse({'ok': True})


class DepartmentMemberRoleView(LoginRequiredMixin, View):
    def post(self, request, company_slug, slug):
        dept = get_object_or_404(_department_queryset(request.user).filter(company=_url_company(request.user, self.kwargs['company_slug'])), slug=slug)
        denied = _require_manage(request, dept)
        if denied:
            return JsonResponse({'error': 'Kein Zugriff'}, status=403)

        try:
            data = json.loads(request.body)
        except ValueError:
            return JsonResponse({'error': 'Ungueltige Daten'}, status=400)

        role = data.get('role')
        if role not in dict(DepartmentMembership.ROLE_CHOICES):
            return JsonResponse({'error': 'Ungueltige Rolle'}, status=400)

        updated = DepartmentMembership.objects.filter(
            department=dept, user_id=data.get('user_id'),
        ).update(role=role)
        if not updated:
            return JsonResponse({'error': 'Mitgliedschaft nicht gefunden'}, status=404)
        return JsonResponse({'ok': True, 'role': role})


class DepartmentSiteAssignView(LoginRequiredMixin, View):
    def get(self, request, company_slug, slug):
        dept = get_object_or_404(_department_queryset(request.user).filter(company=_url_company(request.user, self.kwargs['company_slug'])), slug=slug)
        denied = _require_manage(request, dept)
        if denied:
            return denied

        from sharing.models import GroupShare
        assigned = GroupShare.objects.filter(department=dept, is_active=True).select_related('owner', 'company')
        unassigned = GroupShare.objects.filter(
            department__isnull=True,
            is_active=True,
            company=dept.company,
        ).select_related('owner', 'company')
        return render(request, 'departments/assign_sites.html', {
            'dept': dept,
            'assigned': assigned,
            'unassigned': unassigned,
        })

    def post(self, request, company_slug, slug):
        dept = get_object_or_404(_department_queryset(request.user).filter(company=_url_company(request.user, self.kwargs['company_slug'])), slug=slug)
        denied = _require_manage(request, dept)
        if denied:
            return JsonResponse({'error': 'Kein Zugriff'}, status=403)

        try:
            data = json.loads(request.body)
        except ValueError:
            return JsonResponse({'error': 'Ungueltige Daten'}, status=400)

        action = data.get('action')
        site_id = data.get('site_id')

        from sharing.models import GroupShare
        try:
            site = GroupShare.objects.get(pk=site_id, is_active=True)
        except GroupShare.DoesNotExist:
            return JsonResponse({'error': 'Team-Site nicht gefunden'}, status=404)

        if action == 'assign':
            site.department = dept
            site.company = dept.company
            site.save(update_fields=['department', 'company'])
        elif action == 'unassign':
            if site.department_id == dept.pk:
                site.department = None
                site.save(update_fields=['department'])
        else:
            return JsonResponse({'error': 'Ungueltige Aktion'}, status=400)

        return JsonResponse({'ok': True, 'action': action, 'site_id': site_id, 'site_name': site.group_name})


def _icon_choices():
    return [
        ('bi-building', 'Gebaeude'),
        ('bi-building-fill', 'Gebaeude (gefuellt)'),
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
