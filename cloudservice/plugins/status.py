def is_plugin_enabled(slug):
    try:
        from plugins.models import Plugin

        return Plugin.objects.filter(slug=slug, enabled=True, status='active').exists()
    except Exception:
        return False
