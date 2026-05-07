"""
Views for Core app.
Main dashboard and activity views.
"""

from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from pathlib import Path
from core.models import ActivityLog
from core.navigation import DEFAULT_PLUGIN_APP_SLUG, get_authenticated_home_url
from plugins.hooks import hook_registry, UI_DASHBOARD_WIDGET, UI_APP_PAGE
import logging

logger = logging.getLogger(__name__)


def impressum(request):
    """Öffentliche Impressum-Seite (kein Login erforderlich)."""
    try:
        from landing_editor.providers import get_landing_settings
        lp = get_landing_settings()
    except Exception:
        lp = {}
    try:
        from landing_editor.providers import get_page_content
        page = get_page_content('impressum')
    except Exception:
        page = {}
    return render(request, 'impressum.html', {
        'lp': lp,
        'lp_html': page.get('html', ''),
        'lp_css':  page.get('css', ''),
    })


def home(request):
    """
    Öffentliche Startseite.
    - Nicht eingeloggt → Landingpage (Marketing / Feature-Showcase)
    - Eingeloggt        → MySite Hub
    """
    if request.user.is_authenticated:
        return redirect(get_authenticated_home_url(request))
    try:
        from landing_editor.providers import get_landing_settings
        lp = get_landing_settings()
    except Exception:
        lp = {}
    try:
        from landing_editor.providers import get_page_content
        page = get_page_content('landing')
    except Exception:
        page = {}
    return render(request, 'home.html', {
        'lp': lp,
        'lp_html': page.get('html', ''),
        'lp_css':  page.get('css', ''),
    })


def company_home_redirect(request, workspace_key):
    """Redirect legacy /firmen/<workspace_key>/ URLs to /<workspace_key>/mysite/."""
    from django.urls import reverse
    return redirect(reverse('company_home', kwargs={'workspace_key': workspace_key}), permanent=True)


def company_home(request, workspace_key):
    """Public company landing page at /<workspace_key>/."""
    from accounts.models import Company

    company = get_object_or_404(Company, workspace_key=workspace_key)

    try:
        from landing_editor.providers import get_landing_settings
        lp = get_landing_settings()
    except Exception:
        lp = {}
    try:
        from landing_editor.providers import get_page_content
        page = get_page_content('landing')
    except Exception:
        page = {}

    lp = dict(lp)
    lp['hero_badge'] = company.name
    lp['hero_title_line1'] = company.effective_landing_title
    lp['hero_title_line2'] = company.landing_subtitle or 'Eigener Bereich fuer Teams und Mitarbeiter.'
    lp['hero_subtitle'] = (
        company.landing_subtitle or (
            f"Workspace fuer {company.name} - "
            "mit Bereichen fuer Teams, Mitarbeiter und gemeinsame Inhalte."
        )
    )
    if company.landing_primary_color:
        lp['primary_color'] = company.landing_primary_color
    if company.landing_secondary_color:
        lp['secondary_color'] = company.landing_secondary_color

    return render(request, 'company/landing.html', {
        'lp': lp,
        'lp_html': page.get('html', ''),
        'lp_css': page.get('css', ''),
        'company': company,
    })


def company_landing_settings(request, workspace_key):
    """Company admin: edit the company's landing page."""
    from accounts.models import Company
    from django import forms as django_forms

    company = get_object_or_404(Company, workspace_key=workspace_key)

    if not request.user.is_authenticated:
        return redirect('accounts:login')

    profile = getattr(request.user, 'profile', None)
    is_company_admin = (
        request.user.is_superuser
        or (profile and profile.company == company and profile.is_company_admin)
    )
    if not is_company_admin:
        messages.error(request, 'Kein Zugriff.')
        return redirect('company_home', workspace_key=workspace_key)

    class CompanyLandingForm(django_forms.ModelForm):
        class Meta:
            model = Company
            fields = [
                'landing_title', 'landing_subtitle',
                'landing_logo', 'landing_hero_style',
                'landing_hero_image', 'landing_hero_video',
                'landing_primary_color', 'landing_secondary_color',
                'landing_custom_html', 'landing_custom_css',
            ]

    if request.method == 'POST':
        form = CompanyLandingForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Landing-Page gespeichert.')
            return redirect('company_landing_settings', workspace_key=workspace_key)
    else:
        form = CompanyLandingForm(instance=company)

    return render(request, 'company/landing_settings.html', {
        'company': company,
        'form': form,
    })


def company_landing_builder(request, workspace_key):
    """GrapesJS Sitebuilder für die Firmen-Landingpage."""
    import json as _json
    from accounts.models import Company

    company = get_object_or_404(Company, workspace_key=workspace_key)

    if not request.user.is_authenticated:
        return redirect('accounts:login')

    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or (
        profile and profile.company == company and profile.is_company_admin
    )
    if not is_admin:
        messages.error(request, 'Kein Zugriff.')
        return redirect('company_home', workspace_key=workspace_key)

    default_html = (
        '<section class="lp-section">'
        '<div class="container">'
        '<div class="text-center mb-5">'
        '<div class="section-eyebrow">Funktionen</div>'
        '<h2 class="section-title">Alles was Ihr Team braucht</h2>'
        '</div>'
        '<div class="row g-4">'
        '<div class="col-md-4"><div class="feature-card">'
        '<div class="feature-icon"><i class="bi bi-cloud-upload"></i></div>'
        '<h4>Sicherer Speicher</h4>'
        '<p>Alle Dateien Ihres Teams an einem Ort – sicher und immer verfügbar.</p>'
        '</div></div>'
        '<div class="col-md-4"><div class="feature-card">'
        '<div class="feature-icon"><i class="bi bi-people"></i></div>'
        '<h4>Teamarbeit</h4>'
        '<p>Gemeinsame Ordner, Freigaben und Zusammenarbeit in Echtzeit.</p>'
        '</div></div>'
        '<div class="col-md-4"><div class="feature-card">'
        '<div class="feature-icon"><i class="bi bi-shield-check"></i></div>'
        '<h4>Datensicherheit</h4>'
        '<p>Jeder Nutzer hat seinen eigenen gesicherten Bereich mit individuellen Rechten.</p>'
        '</div></div>'
        '</div>'
        '</div>'
        '</section>'
    )

    return render(request, 'company/landing_builder.html', {
        'company': company,
        'initial_html': company.landing_custom_html or default_html,
        'initial_css': company.landing_custom_css or '',
        'save_url': f'/{workspace_key}/builder/save/',
        'back_url': f'/{workspace_key}/settings/',
        'preview_url': f'/{workspace_key}/',
    })


@require_POST
@login_required
def company_landing_builder_save(request, workspace_key):
    """AJAX: speichert GrapesJS-Output in Company.landing_custom_html/css."""
    import json as _json
    from accounts.models import Company

    company = get_object_or_404(Company, workspace_key=workspace_key)
    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or (
        profile and profile.company == company and profile.is_company_admin
    )
    if not is_admin:
        return JsonResponse({'ok': False, 'error': 'Kein Zugriff'}, status=403)

    try:
        payload = _json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Ungültiges JSON'}, status=400)

    company.landing_custom_html = payload.get('html', '')
    company.landing_custom_css = payload.get('css', '')
    company.save(update_fields=['landing_custom_html', 'landing_custom_css'])
    return JsonResponse({'ok': True})


def company_members(request, workspace_key):
    """Firmen-Mitgliederverwaltung für Company-Admins."""
    import json as _json
    from accounts.models import Company, UserProfile
    from django.contrib.auth import get_user_model
    User = get_user_model()

    company = get_object_or_404(Company, workspace_key=workspace_key)

    if not request.user.is_authenticated:
        return redirect('accounts:login')

    profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or (
        profile and profile.company == company and profile.is_company_admin
    )
    if not is_admin:
        messages.error(request, 'Kein Zugriff.')
        return redirect('company_home', workspace_key=workspace_key)

    # AJAX-Aktionen
    if request.method == 'POST':
        try:
            data = _json.loads(request.body)
        except (ValueError, TypeError):
            return JsonResponse({'ok': False, 'error': 'Ungültige Daten'}, status=400)

        action = data.get('action')

        if action == 'create':
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            password = data.get('password', '').strip()
            role = data.get('role', 'user')

            if not username or not password:
                return JsonResponse({'ok': False, 'error': 'Benutzername und Passwort sind Pflicht'}, status=400)
            if User.objects.filter(username=username).exists():
                return JsonResponse({'ok': False, 'error': f'Benutzername „{username}" ist bereits vergeben'}, status=400)
            if role not in ('user', 'moderator', 'admin'):
                role = 'user'

            new_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            new_user.profile.company = company
            new_user.profile.role = role
            new_user.profile.must_change_password = (role != 'admin')
            new_user.profile.save(update_fields=['company', 'role', 'must_change_password'])
            return JsonResponse({'ok': True, 'username': new_user.username, 'user_id': new_user.pk})

        user_id = data.get('user_id')

        try:
            target_user = User.objects.get(pk=user_id)
            target_profile = target_user.profile
        except (User.DoesNotExist, UserProfile.DoesNotExist):
            return JsonResponse({'ok': False, 'error': 'Benutzer nicht gefunden'}, status=404)

        if action == 'add':
            target_profile.company = company
            target_profile.role = data.get('role', 'user')
            target_profile.save(update_fields=['company', 'role'])
            return JsonResponse({'ok': True})

        elif action == 'set_role':
            if target_profile.company != company and not request.user.is_superuser:
                return JsonResponse({'ok': False, 'error': 'Benutzer gehört nicht zu dieser Firma'}, status=403)
            new_role = data.get('role', 'user')
            if new_role not in ('user', 'moderator', 'admin'):
                return JsonResponse({'ok': False, 'error': 'Ungültige Rolle'}, status=400)
            target_profile.role = new_role
            target_profile.save(update_fields=['role'])
            return JsonResponse({'ok': True})

        elif action == 'remove':
            if target_profile.company != company and not request.user.is_superuser:
                return JsonResponse({'ok': False, 'error': 'Benutzer gehört nicht zu dieser Firma'}, status=403)
            # Eigenen Account nicht entfernen
            if target_user == request.user:
                return JsonResponse({'ok': False, 'error': 'Du kannst dich nicht selbst entfernen'}, status=400)
            target_profile.company = None
            target_profile.role = 'user'
            target_profile.save(update_fields=['company', 'role'])
            return JsonResponse({'ok': True})

        return JsonResponse({'ok': False, 'error': 'Unbekannte Aktion'}, status=400)

    # GET – Seite rendern
    # Rollen-Sync: falls jemand über eine Gruppe Admin ist, aber role='user' hat → korrigieren
    members_qs = UserProfile.objects.filter(company=company).select_related('user')
    for mp in members_qs:
        if mp.role == 'user' and mp.is_company_admin:
            mp.role = 'admin'
            mp.save(update_fields=['role'])
    members = members_qs.order_by('role', 'user__last_name', 'user__username')
    # Benutzer ohne Firma (für "Hinzufügen")
    available_users = User.objects.filter(
        is_active=True, profile__company__isnull=True
    ).select_related('profile').order_by('last_name', 'username')

    return render(request, 'company/members.html', {
        'company': company,
        'members': members,
        'available_users': available_users,
        'role_choices': [('user', 'Benutzer'), ('moderator', 'Moderator'), ('admin', 'Administrator')],
    })


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard"""
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.models import StorageFile, StorageFolder

        context['total_files'] = StorageFile.objects.filter(
            owner=self.request.user
        ).count()

        context['total_folders'] = StorageFolder.objects.filter(
            owner=self.request.user
        ).count()

        context['recent_files'] = StorageFile.objects.filter(
            owner=self.request.user
        ).order_by('-created_at')[:5]

        context['storage_used'] = self.request.user.profile.get_storage_used_mb()
        context['storage_quota'] = self.request.user.profile.storage_quota / (1024 * 1024 * 1024)

        return context


def dashboard(request):
    """Dashboard view function"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    return DashboardView.as_view()(request)


class ActivityLogView(LoginRequiredMixin, ListView):
    """Activity log view"""
    template_name = 'core/activity_log.html'
    context_object_name = 'activities'
    paginate_by = 50

    def get_queryset(self):
        return ActivityLog.objects.filter(user=self.request.user)


def activity_log(request):
    """Activity log view function"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    return ActivityLogView.as_view()(request)


def search(request):
    """Globale Volltext-Suche über alle Inhaltstypen."""
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    query = request.GET.get('q', '').strip()
    results = {}
    total = 0

    if query:
        from core.models import StorageFile, StorageFolder
        from django.contrib.auth.models import User
        from django.db.models import Q

        # Dateien & Ordner (eigene)
        files = StorageFile.objects.filter(
            owner=request.user,
            name__icontains=query
        ).select_related('owner')[:20]

        folders = StorageFolder.objects.filter(
            owner=request.user,
            name__icontains=query
        )[:10]

        # News-Artikel
        try:
            from news.models import NewsArticle
            news = NewsArticle.objects.filter(
                is_published=True
            ).filter(
                Q(title__icontains=query) |
                Q(summary__icontains=query) |
                Q(content__icontains=query) |
                Q(tags__icontains=query)
            ).select_related('author', 'category')[:10]
        except Exception:
            news = []

        # Team-Sites (GroupShare)
        try:
            from sharing.models import GroupShare
            team_sites = GroupShare.objects.filter(
                Q(group_name__icontains=query)
            ).filter(is_active=True)[:10]
        except Exception:
            team_sites = []

        # Team-Site News
        try:
            from sharing.models import TeamSiteNews
            team_news = TeamSiteNews.objects.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query)
            ).select_related('group', 'author')[:10]
        except Exception:
            team_news = []

        # Personen (nur für eingeloggte)
        people = User.objects.filter(is_active=True).filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )[:8]

        results = {
            'files': list(files),
            'folders': list(folders),
            'news': list(news),
            'team_sites': list(team_sites),
            'team_news': list(team_news),
            'people': list(people),
        }
        total = sum(len(v) for v in results.values())

    return render(request, 'core/search.html', {
        'query': query,
        'results': results,
        'total': total,
    })


def search_suggest(request):
    """AJAX-Autocomplete für die Navbar-Suche."""
    import json
    from django.http import JsonResponse

    if not request.user.is_authenticated:
        return JsonResponse({'suggestions': []})

    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'suggestions': []})

    from core.models import StorageFile
    from django.db.models import Q
    suggestions = []

    # Dateien
    for f in StorageFile.objects.filter(owner=request.user, name__icontains=q)[:5]:
        suggestions.append({'label': f.name, 'type': 'file', 'icon': 'bi-file-earmark', 'url': f'/storage/file/{f.id}/'})

    # News
    try:
        from news.models import NewsArticle
        for a in NewsArticle.objects.filter(is_published=True, title__icontains=q)[:5]:
            suggestions.append({'label': a.title, 'type': 'news', 'icon': 'bi-newspaper', 'url': f'/news/{a.slug}/'})
    except Exception:
        pass

    # Personen
    from django.contrib.auth.models import User
    for u in User.objects.filter(is_active=True).filter(
        Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
    )[:3]:
        name = u.get_full_name() or u.username
        suggestions.append({'label': name, 'type': 'person', 'icon': 'bi-person', 'url': f'/accounts/profile/{u.username}/'})

    return JsonResponse({'suggestions': suggestions[:10]})


class SettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Settings page with plugin management"""
    template_name = 'core/settings.html'

    def test_func(self):
        """Only allow superusers/admins"""
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get plugin data
        try:
            from plugins.models import Plugin, PluginLog
            context['plugins'] = Plugin.objects.all().order_by('-uploaded_at')
            context['plugin_logs'] = PluginLog.objects.all().order_by('-created_at')[:20]
            context['has_plugins'] = Plugin.objects.exists()
        except Exception as e:
            logger.error(f"Failed to load plugin data: {e}")
            context['plugins'] = []
            context['plugin_logs'] = []
            context['has_plugins'] = False

        return context

    def post(self, request, *args, **kwargs):
        """Handle plugin upload"""
        if not self.test_func():
            messages.error(request, 'Access denied')
            return redirect('core:settings')

        zip_file = request.FILES.get('zip_file')
        if not zip_file:
            messages.error(request, '❌ No file selected')
            return redirect('core:settings')

        try:
            from plugins.loader import PluginLoader
            from plugins.models import Plugin, PluginLog

            loader = PluginLoader()

            # Save uploaded file temporarily
            temp_path = Path('/tmp') / zip_file.name
            with open(temp_path, 'wb+') as f:
                for chunk in zip_file.chunks():
                    f.write(chunk)

            logger.info(f"Uploaded plugin ZIP: {zip_file.name}")

            # Validate ZIP
            manifest = loader.validate_zip(temp_path)
            logger.info(f"ZIP validation passed: {manifest['name']}")

            # Create plugin record
            plugin = Plugin.objects.create(
                name=manifest['name'],
                slug=manifest['slug'],
                version=manifest['version'],
                author=manifest.get('author', 'Unknown'),
                description=manifest.get('description', ''),
                zip_file=zip_file,
                manifest=manifest,
                installed_by=request.user,
                status='inactive'
            )

            logger.info(f"Created plugin record: {plugin.id}")

            # Extract plugin
            extract_dir = loader.extract_plugin(str(plugin.id), temp_path)
            plugin.extracted_path = str(extract_dir)
            plugin.save()

            # Log the action
            PluginLog.objects.create(
                plugin=plugin,
                action='uploaded',
                user=request.user,
                message=f"Plugin uploaded by {request.user.username}"
            )

            messages.success(
                request,
                f'✅ Plugin "{plugin.name}" uploaded successfully. Click "Activate" to enable.'
            )
            logger.info(f"Admin {request.user.username} uploaded plugin {plugin.name}")

        except ValueError as e:
            messages.error(request, f'❌ Invalid plugin: {str(e)}')
            logger.error(f"Plugin upload validation failed: {e}")

        except Exception as e:
            messages.error(request, f'❌ Upload failed: {str(e)}')
            logger.error(f"Plugin upload failed: {e}")

        return redirect('core:settings')


def settings(request):
    """Settings view function"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    return SettingsView.as_view()(request)


class DebugPluginsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Debug plugins view - for development/troubleshooting"""
    template_name = 'core/debug_plugins.html'

    def test_func(self):
        """Only allow superusers"""
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get plugins
        try:
            from plugins.models import Plugin
            context['plugins'] = Plugin.objects.all().order_by('-uploaded_at')
        except Exception as e:
            context['plugins'] = []
            context['error'] = str(e)

        # Get hook information
        try:
            from plugins.hooks import hook_registry, FILE_PREVIEW_PROVIDER

            hooks_info = "=== HOOK REGISTRY DEBUG ===\n\n"

            # Get all registered hooks
            handlers = hook_registry.get_handlers(FILE_PREVIEW_PROVIDER)
            hooks_info += f"FILE_PREVIEW_PROVIDER handlers: {len(handlers)}\n"

            if handlers:
                for i, handler in enumerate(handlers):
                    hooks_info += f"  [{i}] {handler.__name__} (class: {handler})\n"
            else:
                hooks_info += "  (No handlers registered)\n"

            # Show internal hook structure
            hooks_info += f"\nInternal _hooks dict:\n"
            if hasattr(hook_registry, '_hooks'):
                for hook_name, hook_list in hook_registry._hooks.items():
                    hooks_info += f"  {hook_name}:\n"
                    for hook_info in hook_list:
                        hooks_info += f"    - Handler: {hook_info['handler']}\n"
                        hooks_info += f"      Priority: {hook_info['priority']}\n"
                        hooks_info += f"      Metadata: {hook_info['metadata']}\n"

        except Exception as e:
            hooks_info = f"Error loading hooks: {e}"
            logger.error(f"Debug hooks error: {e}", exc_info=True)

        context['hooks_info'] = hooks_info

        return context


def debug_plugins(request):
    """Debug plugins view function"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    return DebugPluginsView.as_view()(request)


class LandingView(LoginRequiredMixin, TemplateView):
    """
    Landing page with widget grid.
    Shows widgets from plugins and built-in widgets.
    """
    template_name = 'core/landing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Collect all widgets from hooks
        widgets = []

        # Get widget providers from hook registry
        handlers = hook_registry.get_handlers(UI_DASHBOARD_WIDGET)
        logger.debug(f"Found {len(handlers)} widget handlers")

        for handler in handlers:
            try:
                # Instantiate the widget provider
                provider = handler()

                # Render the widget
                widget_data = provider.render(self.request)
                if widget_data:
                    widgets.append(widget_data)
                    logger.debug(f"Added widget: {widget_data['id']}")

            except Exception as e:
                logger.error(f"Failed to load widget from {handler}: {e}")

        # Sort widgets by order
        widgets.sort(key=lambda w: w['order'])

        context['widgets'] = widgets
        return context


def landing(request):
    """Landing page view function"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    return LandingView.as_view()(request)


class PluginAppPageView(LoginRequiredMixin, TemplateView):
    """Render plugin-provided app pages."""

    def get(self, request, *args, **kwargs):
        slug = kwargs['slug']
        handlers = hook_registry.get_handlers(UI_APP_PAGE, slug=slug)
        if not handlers:
            if slug == DEFAULT_PLUGIN_APP_SLUG:
                return redirect(get_authenticated_home_url(request))
            raise Http404('Plugin page not found')

        provider = handlers[0]()
        if not provider.is_visible(request):
            if slug == DEFAULT_PLUGIN_APP_SLUG:
                return redirect(get_authenticated_home_url(request))
            raise Http404('Plugin page not available')

        context = provider.render(request)
        return render(request, provider.get_template_name(), context)


def plugin_app(request, slug):
    """Plugin application page view."""
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    return PluginAppPageView.as_view()(request, slug=slug)


def help_page(request):
    """Help page view"""
    return render(request, 'core/help.html')


def help_developer(request):
    """Developer documentation view"""
    return render(request, 'core/help_developer.html')


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def notifications_list(request):
    """Alle Benachrichtigungen des Users — als vollständige Seite."""
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    from core.models import Notification
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    # Alle als gelesen markieren beim Öffnen der Seite
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'core/notifications.html', {'notifications': notifs})


def notifications_unread_count(request):
    """AJAX: Anzahl ungelesener Benachrichtigungen."""
    from django.http import JsonResponse
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
    from core.models import Notification
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


def notifications_mark_read(request, pk):
    """AJAX: Eine einzelne Benachrichtigung als gelesen markieren."""
    from django.http import JsonResponse
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False}, status=403)
    from core.models import Notification
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return JsonResponse({'ok': True})


def notifications_mark_all_read(request):
    """AJAX: Alle als gelesen markieren."""
    from django.http import JsonResponse
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False}, status=403)
    from core.models import Notification
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})


def notifications_dropdown(request):
    """AJAX: Letzte 8 Benachrichtigungen als HTML-Fragment für das Dropdown."""
    from django.http import JsonResponse
    if not request.user.is_authenticated:
        return JsonResponse({'html': ''})
    from core.models import Notification
    notifs = list(
        Notification.objects.filter(user=request.user)
        .order_by('-created_at')[:8]
        .values('id', 'title', 'message', 'url', 'is_read', 'notification_type', 'created_at')
    )
    unread = Notification.objects.filter(user=request.user, is_read=False).count()
    # Datumsformat für JS
    for n in notifs:
        n['created_at'] = n['created_at'].strftime('%d.%m.%Y %H:%M')
    return JsonResponse({'notifications': notifs, 'unread': unread})
