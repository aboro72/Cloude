from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom Django admin configuration for the unified User model.
    """

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {
            'fields': (
                'first_name', 'last_name', 'phone', 'bio',
                'website', 'avatar'
            )
        }),
        (_('Role & Permissions'), {
            'fields': (
                'role', 'support_level', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            )
        }),
        (_('Storage & Quota'), {
            'fields': ('storage_quota',)
        }),
        (_('Location & Preferences'), {
            'fields': (
                'department', 'location', 'street', 'postal_code',
                'city', 'country', 'language', 'timezone', 'theme'
            ),
            'classes': ('collapse',)
        }),
        (_('OAuth Integration'), {
            'fields': ('microsoft_id', 'microsoft_token'),
            'classes': ('collapse',)
        }),
        (_('Security'), {
            'fields': (
                'is_active', 'email_verified', 'is_two_factor_enabled',
                'force_password_change'
            )
        }),
        (_('Important dates'), {
            'fields': (
                'last_login', 'last_activity', 'created_at', 'updated_at'
            )
        }),
        (_('App Settings'), {
            'fields': ('app_settings',),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'password1', 'password2',
                'first_name', 'last_name', 'role'
            ),
        }),
    )

    list_display = (
        'email', 'username', 'first_name', 'last_name',
        'role', 'is_active', 'email_verified', 'created_at'
    )
    list_filter = (
        'role', 'is_active', 'email_verified', 'is_two_factor_enabled',
        'created_at', 'last_login'
    )
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'last_activity')

    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user role"""
        form = super().get_form(request, obj, **kwargs)
        # Add custom form logic if needed
        return form

    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        if not change:
            # New user - set password properly
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """Customize queryset based on user permissions"""
        qs = super().get_queryset(request)
        # Superusers can see all users
        if request.user.is_superuser:
            return qs
        # Other admins can see all except superusers
        return qs.exclude(is_superuser=True)
