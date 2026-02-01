"""
Views for Core app.
Main dashboard and activity views.
"""

from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, redirect
from django.contrib import messages
from pathlib import Path
from core.models import ActivityLog
from plugins.hooks import hook_registry, UI_DASHBOARD_WIDGET
import logging

logger = logging.getLogger(__name__)


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
    """Search view function"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    query = request.GET.get('q', '')
    from core.models import StorageFile, StorageFolder

    files = StorageFile.objects.filter(
        owner=request.user,
        name__icontains=query
    )

    folders = StorageFolder.objects.filter(
        owner=request.user,
        name__icontains=query
    )

    return render(request, 'core/search.html', {
        'query': query,
        'files': files,
        'folders': folders
    })


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


def help_page(request):
    """Help page view"""
    return render(request, 'core/help.html')


def help_developer(request):
    """Developer documentation view"""
    return render(request, 'core/help_developer.html')
