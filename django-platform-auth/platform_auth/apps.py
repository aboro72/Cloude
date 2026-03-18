from django.apps import AppConfig


class PlatformAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'platform_auth'
    verbose_name = 'Platform Authentication'

    def ready(self):
        import platform_auth.signals  # noqa
