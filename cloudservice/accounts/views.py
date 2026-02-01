"""
Views for Accounts app.
User authentication and profile management.
"""

from django.views.generic import CreateView, UpdateView, TemplateView, ListView
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import PasswordChangeView as DjangoPasswordChangeView
from django.contrib.auth.models import User
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from accounts.models import UserProfile
import logging

logger = logging.getLogger(__name__)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(DjangoLoginView):
    """User login"""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = False
    success_url = reverse_lazy('core:landing')

    def get(self, request, *args, **kwargs):
        """Handle GET requests - show login form"""
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        """Called when login form is valid"""
        return super().form_valid(form)


class RegisterView(CreateView):
    """User registration"""
    template_name = 'accounts/register.html'
    model = User
    fields = ['username', 'email', 'first_name', 'last_name', 'password']
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view"""
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.request.user.profile
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit user profile"""
    template_name = 'accounts/profile_edit.html'
    model = UserProfile
    fields = ['phone_number', 'avatar', 'bio', 'website', 'language', 'timezone', 'theme']
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user.profile


class PasswordChangeView(DjangoPasswordChangeView):
    """Change password"""
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')


class SettingsView(LoginRequiredMixin, TemplateView):
    """User settings"""
    template_name = 'accounts/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.request.user.profile
        return context


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
