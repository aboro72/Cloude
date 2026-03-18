import re

from django import forms
from django.contrib import admin

from accounts.models import AuditLog, PasswordReset, TwoFactorAuth, UserProfile, UserSession


class UserProfileAdminForm(forms.ModelForm):
    storage_quota_display = forms.CharField(
        label='Speicherlimit',
        help_text='Zulaessige Formate: z.B. 500 MB, 10 GB, 1024 KB oder Bytes als Zahl.',
    )

    class Meta:
        model = UserProfile
        exclude = ('storage_quota',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        quota_bytes = self.instance.storage_quota if self.instance and self.instance.pk else self.initial.get('storage_quota')
        quota_bytes = quota_bytes or self.fields['storage_quota'].initial or 0
        self.fields['storage_quota_display'].initial = self.format_quota(quota_bytes)

    @staticmethod
    def format_quota(quota_bytes):
        if quota_bytes >= 1024 ** 3 and quota_bytes % (1024 ** 3) == 0:
            return f'{quota_bytes // (1024 ** 3)} GB'
        if quota_bytes >= 1024 ** 2 and quota_bytes % (1024 ** 2) == 0:
            return f'{quota_bytes // (1024 ** 2)} MB'
        if quota_bytes >= 1024 and quota_bytes % 1024 == 0:
            return f'{quota_bytes // 1024} KB'
        return str(quota_bytes)

    @staticmethod
    def parse_quota(value):
        cleaned = value.strip().upper().replace(',', '.')
        match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(B|BYTE|BYTES|KB|MB|GB)?', cleaned)
        if not match:
            raise forms.ValidationError('Ungueltiges Format. Beispiel: 500 MB oder 10 GB.')

        amount = float(match.group(1))
        unit = match.group(2) or 'B'
        factors = {
            'B': 1,
            'BYTE': 1,
            'BYTES': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
        }
        return int(amount * factors[unit])

    def clean_storage_quota_display(self):
        value = self.cleaned_data['storage_quota_display']
        quota_bytes = self.parse_quota(value)
        min_quota = UserProfile._meta.get_field('storage_quota').validators[0].limit_value
        if quota_bytes < min_quota:
            raise forms.ValidationError('Das Speicherlimit muss mindestens 1 MB betragen.')
        return quota_bytes

    def clean(self):
        cleaned_data = super().clean()
        quota_bytes = cleaned_data.get('storage_quota_display')
        if quota_bytes is not None:
            cleaned_data['storage_quota'] = quota_bytes
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        quota_bytes = self.cleaned_data.get('storage_quota_display')
        if quota_bytes is not None:
            instance.storage_quota = quota_bytes
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = (
        'user',
        'role',
        'storage_quota_gb',
        'storage_used_gb',
        'storage_usage_percent',
        'is_active',
    )
    list_filter = ('role', 'is_active', 'is_email_verified', 'is_two_factor_enabled')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'last_login_at', 'storage_used_gb', 'storage_quota_bytes')
    fieldsets = (
        ('Benutzer', {'fields': ('user', 'role', 'is_active')}),
        ('Speicher', {'fields': ('storage_quota_display', 'storage_quota_bytes', 'storage_used_gb')}),
        (
            'Profil',
            {
                'fields': (
                    'phone_number',
                    'avatar',
                    'bio',
                    'website',
                    'language',
                    'timezone',
                    'theme',
                    'design_variant',
                    'color_preset',
                    'primary_color',
                    'secondary_color',
                    'mysite_hero_style',
                    'mysite_hero_image',
                    'mysite_hero_video',
                )
            }
        ),
        ('Sicherheit', {'fields': ('is_email_verified', 'is_two_factor_enabled', 'last_login_at')}),
        ('Metadaten', {'fields': ('created_at', 'updated_at')}),
    )

    @admin.display(description='Quota (GB)')
    def storage_quota_gb(self, obj):
        return round(obj.storage_quota / (1024 ** 3), 2)

    @admin.display(description='Belegt (GB)')
    def storage_used_gb(self, obj):
        return round(obj.get_storage_used() / (1024 ** 3), 2)

    @admin.display(description='Nutzung (%)')
    def storage_usage_percent(self, obj):
        return round(obj.get_storage_used_percentage(), 1)

    @admin.display(description='Quota (Bytes)')
    def storage_quota_bytes(self, obj):
        return obj.storage_quota


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'device_name', 'is_active', 'last_activity', 'expires_at')
    list_filter = ('is_active', 'os_type')
    search_fields = ('user__username', 'ip_address', 'device_name')


@admin.register(TwoFactorAuth)
class TwoFactorAuthAdmin(admin.ModelAdmin):
    list_display = ('user', 'method', 'is_enabled', 'enabled_at')
    list_filter = ('is_enabled', 'method')
    search_fields = ('user__username', 'phone_number')


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_used',)
    search_fields = ('user__username', 'token')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'created_at')
    list_filter = ('action',)
    search_fields = ('user__username', 'description', 'ip_address')
    readonly_fields = ('created_at',)
