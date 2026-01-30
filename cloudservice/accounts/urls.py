"""
URL configuration for Accounts app.
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from accounts import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('profile/password/', views.PasswordChangeView.as_view(), name='password_change'),

    # Settings
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('settings/two-factor/', views.TwoFactorSetupView.as_view(), name='two_factor_setup'),
    path('settings/sessions/', views.SessionManagementView.as_view(), name='sessions'),

    # Email verification
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),

    # API tokens
    path('api-tokens/', views.APITokenListView.as_view(), name='api_tokens'),
]
