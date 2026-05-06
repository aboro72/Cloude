"""
Views for Accounts app.
User authentication and profile management.
"""

import json

from django.views.generic import CreateView, UpdateView, TemplateView, ListView
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import PasswordChangeView as DjangoPasswordChangeView
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.models import Group, Permission, User
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from django.views import View
from django.http import JsonResponse
from accounts.models import UserProfile
from accounts.forms import AppearanceSettingsForm, RegisterForm
from core.navigation import get_authenticated_home_url
import logging

logger = logging.getLogger(__name__)


@method_decorator(ensure_csrf_cookie, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class LoginView(DjangoLoginView):
    """User login"""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = False

    def get(self, request, *args, **kwargs):
        """Handle GET requests - show login form"""
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        """Called when login form is valid"""
        return super().form_valid(form)

    def get_success_url(self):
        return get_authenticated_home_url(self.request)


class LogoutView(View):
    """Log out the current user and redirect to landing page."""

    next_page = reverse_lazy('home')

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect(self.next_page)

    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect(self.next_page)


class RegisterView(CreateView):
    """User registration"""
    template_name = 'accounts/register.html'
    model = User
    form_class = RegisterForm

    def get_success_url(self):
        try:
            workspace_key = self.object.profile.company.workspace_key
            from django.urls import reverse
            return reverse('company_home', kwargs={'workspace_key': workspace_key})
        except Exception:
            return reverse_lazy('accounts:login')


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view"""
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['profile'] = profile
        context['storage_used_mb'] = profile.get_storage_used_mb()
        context['storage_quota_gb'] = profile.storage_quota / (1024 ** 3)
        context['storage_remaining_mb'] = profile.get_storage_remaining_mb()
        context['storage_percentage'] = round(profile.get_storage_used_percentage(), 1)

        completed_fields = [
            bool(self.request.user.first_name or self.request.user.last_name),
            bool(self.request.user.email),
            bool(profile.phone_number),
            bool(profile.bio),
            bool(profile.website),
            bool(profile.avatar),
        ]
        context['profile_completion'] = int((sum(completed_fields) / len(completed_fields)) * 100)
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit user profile"""
    template_name = 'accounts/profile_edit.html'
    model = UserProfile
    fields = ['phone_number', 'avatar', 'bio', 'website', 'language', 'timezone', 'theme',
              'job_title', 'department', 'location', 'manager']
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user.profile


class PasswordChangeView(DjangoPasswordChangeView):
    """Change password"""
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        profile = getattr(self.request.user, 'profile', None)
        if profile and profile.must_change_password:
            profile.must_change_password = False
            profile.save(update_fields=['must_change_password'])
        return response


class SettingsView(LoginRequiredMixin, TemplateView):
    """User settings"""
    template_name = 'accounts/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.request.user.profile
        context['form'] = kwargs.get('form') or AppearanceSettingsForm(instance=self.request.user.profile)
        return context

    def post(self, request, *args, **kwargs):
        form = AppearanceSettingsForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Design-Einstellungen wurden gespeichert.')
            return redirect('accounts:settings')

        messages.error(request, 'Bitte pruefen Sie die Eingaben in den Design-Einstellungen.')
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class TwoFactorSetupView(LoginRequiredMixin, TemplateView):
    """Setup two-factor authentication"""
    template_name = 'accounts/two_factor_setup.html'


class SessionManagementView(LoginRequiredMixin, ListView):
    """Manage user sessions"""
    template_name = 'accounts/sessions.html'
    context_object_name = 'sessions'

    def get_queryset(self):
        from accounts.models import UserSession
        return UserSession.objects.filter(user=self.request.user, is_active=True)


def verify_email(request, token):
    """Verify email address"""
    # Implementation for email verification
    pass


class APITokenListView(LoginRequiredMixin, ListView):
    """Manage API tokens"""
    template_name = 'accounts/api_tokens.html'
    context_object_name = 'tokens'

    def get_queryset(self):
        # Implementation for API tokens
        return []


class PublicProfileView(LoginRequiredMixin, TemplateView):
    """Öffentliches Profil eines anderen Nutzers ansehen."""
    template_name = 'accounts/public_profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.shortcuts import get_object_or_404
        from django.contrib.auth.models import User
        user = get_object_or_404(User, username=self.kwargs['username'], is_active=True)
        context['viewed_user'] = user
        context['viewed_profile'] = getattr(user, 'profile', None)
        # Direkte Berichte (wer reported an diesen User)
        context['direct_reports'] = User.objects.filter(
            profile__manager=user, is_active=True
        ).select_related('profile')
        return context


class GroupManagementView(LoginRequiredMixin, View):
    """Gruppen- und Berechtigungsverwaltung (nur Staff)."""
    template_name = 'accounts/group_management.html'

    def _require_staff(self, request):
        profile = getattr(request.user, 'profile', None)
        if not request.user.is_superuser and not (profile and profile.is_company_admin):
            return render(request, '403.html', {
                'error_message': 'Nur Administratoren dürfen Gruppen und Berechtigungen verwalten.',
            }, status=403)
        return None

    def get(self, request):
        denied = self._require_staff(request)
        if denied:
            return denied

        groups = Group.objects.prefetch_related('permissions', 'user_set').order_by('name')
        all_users = User.objects.filter(is_active=True).order_by('last_name', 'username')

        # Build permission map per group for display
        group_data = []
        for g in groups:
            group_data.append({
                'group': g,
                'members': g.user_set.select_related('profile').all(),
                'permissions': g.permissions.select_related('content_type').order_by('content_type__model', 'codename'),
            })

        return render(request, self.template_name, {
            'group_data': group_data,
            'all_users': all_users,
        })

    def post(self, request):
        denied = self._require_staff(request)
        if denied:
            return JsonResponse({'error': 'Kein Zugriff'}, status=403)

        try:
            data = json.loads(request.body)
        except ValueError:
            return JsonResponse({'error': 'Ungültige Daten'}, status=400)

        action = data.get('action')
        group_id = data.get('group_id')
        user_id = data.get('user_id')

        try:
            group = Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            return JsonResponse({'error': 'Gruppe nicht gefunden'}, status=404)

        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Nutzer nicht gefunden'}, status=404)

        if action == 'add':
            group.user_set.add(user)
        elif action == 'remove':
            group.user_set.remove(user)
        else:
            return JsonResponse({'error': 'Ungültige Aktion'}, status=400)

        return JsonResponse({
            'ok': True,
            'action': action,
            'group_name': group.name,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
        })
