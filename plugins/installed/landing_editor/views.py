import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
@require_POST
def save_settings(request):
    """AJAX: persist landing page / page builder settings to Plugin.settings."""
    if not request.user.is_staff:
        return JsonResponse({'ok': False, 'error': 'Kein Zugriff'}, status=403)

    try:
        payload = json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Ungültiges JSON'}, status=400)

    try:
        from plugins.models import Plugin
        plugin, _ = Plugin.objects.get_or_create(
            slug='landing-editor',
            defaults={
                'name': 'Landing Page Editor',
                'version': '1.0.0',
                'author': 'CloudService Team',
                'description': 'Visueller Webbaukasten für die Startseite.',
                'status': 'active',
                'is_local': True,
            },
        )
        current = dict(plugin.settings or {})
        action = payload.get('action', 'save_settings')

        if action == 'save_page':
            # GrapesJS page content: {action, page, html, css}
            page_slug = payload.get('page', 'landing')
            pages = dict(current.get('pages', {}))
            pages[page_slug] = {
                'html': payload.get('html', ''),
                'css':  payload.get('css', ''),
            }
            current['pages'] = pages

        elif action == 'save_mysite':
            # MySite widget config: {action, widgets: [...]}
            current['mysite_widgets'] = payload.get('widgets', [])

        else:
            # Legacy: flat key-value update (old sidebar form)
            current.update({k: v for k, v in payload.items() if k != 'action'})

        plugin.settings = current
        plugin.save(update_fields=['settings'])
        return JsonResponse({'ok': True})

    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=500)
