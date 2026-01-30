"""
Views for Core app.
Main dashboard and activity views.
"""

from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from core.models import ActivityLog


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
