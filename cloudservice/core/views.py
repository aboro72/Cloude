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
