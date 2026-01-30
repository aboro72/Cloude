"""
Views for Sharing app.
File and folder sharing management.
"""

from django.views.generic import CreateView, DeleteView, ListView, TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.http import JsonResponse, FileResponse
from django.db.models import Q

from sharing.models import UserShare, PublicLink, GroupShare, ShareLog
from core.models import StorageFile, StorageFolder
import logging

logger = logging.getLogger(__name__)


class ShareView(LoginRequiredMixin, CreateView):
    """Share file or folder with user"""
    template_name = 'sharing/share.html'
    model = UserShare
    fields = ['shared_with', 'permission', 'message']

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_type = self.kwargs.get('content_type')
        object_id = self.kwargs.get('object_id')

        if content_type == 'file':
            context['object'] = get_object_or_404(
                StorageFile,
                id=object_id,
                owner=self.request.user
            )
        elif content_type == 'folder':
            context['object'] = get_object_or_404(
                StorageFolder,
                id=object_id,
                owner=self.request.user
            )

        return context


class SharesListView(LoginRequiredMixin, ListView):
    """List shares created and received"""
    template_name = 'sharing/shares_list.html'
    context_object_name = 'shares'

    def get_queryset(self):
        """Get shares for current user"""
        return UserShare.objects.filter(
            Q(owner=self.request.user) | Q(shared_with=self.request.user)
        )


class DeleteShareView(LoginRequiredMixin, DeleteView):
    """Delete share"""
    model = UserShare
    success_url = reverse_lazy('sharing:shares_list')

    def get_queryset(self):
        return UserShare.objects.filter(owner=self.request.user)


class PublicLinkView(DetailView):
    """View public link"""
    template_name = 'sharing/public_link.html'
    model = PublicLink
    slug_field = 'token'
    slug_url_kwarg = 'token'
    context_object_name = 'link'

    def get_queryset(self):
        return PublicLink.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        link = self.get_object()

        if link.is_expired():
            context['is_expired'] = True
            return context

        link.increment_view_count()

        # Get shared object details
        if link.content_object:
            context['shared_object'] = link.content_object

        return context


class PublicDownloadView(DetailView):
    """Download from public link"""
    model = PublicLink
    slug_field = 'token'
    slug_url_kwarg = 'token'

    def get_queryset(self):
        return PublicLink.objects.filter(is_active=True)

    def get(self, request, *args, **kwargs):
        link = self.get_object()

        if link.is_expired():
            return render(request, 'sharing/link_expired.html')

        if not link.allow_download:
            return render(request, 'sharing/download_not_allowed.html')

        # Check password if required
        if link.password_hash:
            password = request.GET.get('password')
            if not password or not link.check_password(password):
                return render(request, 'sharing/password_required.html', {
                    'link': link
                })

        # Download file
        if isinstance(link.content_object, StorageFile):
            file_obj = link.content_object
            link.increment_download_count()

            response = FileResponse(
                file_obj.file.open('rb'),
                as_attachment=True
            )
            response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'
            return response

        return render(request, 'sharing/cannot_download.html')


class PublicLinksListView(LoginRequiredMixin, ListView):
    """List public links"""
    template_name = 'sharing/links_list.html'
    context_object_name = 'links'

    def get_queryset(self):
        return PublicLink.objects.filter(owner=self.request.user)


class PublicLinkSettingsView(LoginRequiredMixin, DetailView):
    """Public link settings"""
    template_name = 'sharing/link_settings.html'
    model = PublicLink
    context_object_name = 'link'

    def get_queryset(self):
        return PublicLink.objects.filter(owner=self.request.user)


class DeletePublicLinkView(LoginRequiredMixin, DeleteView):
    """Delete public link"""
    model = PublicLink
    success_url = reverse_lazy('sharing:links_list')

    def get_queryset(self):
        return PublicLink.objects.filter(owner=self.request.user)


class GroupsListView(LoginRequiredMixin, ListView):
    """List groups"""
    template_name = 'sharing/groups_list.html'
    context_object_name = 'groups'

    def get_queryset(self):
        return GroupShare.objects.filter(owner=self.request.user)


class CreateGroupView(LoginRequiredMixin, CreateView):
    """Create sharing group"""
    template_name = 'sharing/create_group.html'
    model = GroupShare
    fields = ['group_name', 'members']
    success_url = reverse_lazy('sharing:groups_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class GroupShareView(LoginRequiredMixin, CreateView):
    """Share with group"""
    template_name = 'sharing/group_share.html'
    model = GroupShare
    fields = ['permission']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = get_object_or_404(
            GroupShare,
            id=self.kwargs.get('group_id'),
            owner=self.request.user
        )
        return context


class SharedWithMeView(LoginRequiredMixin, ListView):
    """View files/folders shared with me"""
    template_name = 'sharing/shared_with_me.html'
    context_object_name = 'shares'

    def get_queryset(self):
        return UserShare.objects.filter(
            shared_with=self.request.user,
            is_active=True
        )
