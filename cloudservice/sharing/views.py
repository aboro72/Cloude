"""
Views for Sharing app.
File and folder sharing management.
"""

from django.db import models
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.http import JsonResponse, FileResponse, Http404
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from departments.models import Company
from sharing.models import UserShare, PublicLink, GroupShare, ShareLog, TeamSiteNews
from sharing.forms import TeamSiteNewsForm
from core.models import ActivityLog, StorageFile, StorageFolder
from core.navigation import get_optional_plugin_app_url
import logging

logger = logging.getLogger(__name__)


def _user_company(user):
    if not user or not user.is_authenticated or not hasattr(user, 'profile'):
        return None
    return user.profile.company


def _url_company(user, company_slug):
    queryset = Company.objects.filter(slug=company_slug, is_active=True)
    user_company = _user_company(user)
    if user_company and not user.has_perm('departments.manage_any_company'):
        queryset = queryset.filter(pk=user_company.pk)
    return get_object_or_404(queryset)


def _group_queryset(user):
    queryset = GroupShare.objects.filter(
        Q(owner=user) | Q(team_leaders=user) | Q(members=user)
    ).distinct()
    company = _user_company(user)
    if company:
        queryset = queryset.filter(company=company)
    return queryset


class ShareView(LoginRequiredMixin, CreateView):
    """Share file or folder with user"""
    template_name = 'sharing/share.html'
    model = UserShare
    fields = ['shared_with', 'permission', 'message']
    success_url = reverse_lazy('sharing:shares_list')

    def get_context_data(self, **kwargs):
        from django.contrib.auth.models import User

        context = super().get_context_data(**kwargs)
        content_type = self.kwargs.get('content_type')
        object_id = self.kwargs.get('object_id')

        # Get object being shared
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

        # Get list of users (exclude current user)
        context['users'] = User.objects.exclude(id=self.request.user.id).order_by('username')

        return context

    def form_valid(self, form):
        from django.contrib.contenttypes.models import ContentType as CT

        content_type = self.kwargs.get('content_type')
        object_id = self.kwargs.get('object_id')

        form.instance.owner = self.request.user

        if content_type == 'file':
            ct = CT.objects.get_for_model(StorageFile)
        else:
            ct = CT.objects.get_for_model(StorageFolder)

        form.instance.content_type = ct
        form.instance.object_id = object_id

        return super().form_valid(form)


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
    pk_url_kwarg = 'share_id'

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
    pk_url_kwarg = 'link_id'

    def get_queryset(self):
        return PublicLink.objects.filter(owner=self.request.user)

    def post(self, request, *args, **kwargs):
        """Handle settings update"""
        link = self.get_object()

        # Update fields
        link.title = request.POST.get('title', '')
        link.description = request.POST.get('description', '')
        link.permission = request.POST.get('permission', 'view')
        link.allow_download = 'allow_download' in request.POST
        link.is_active = 'is_active' in request.POST

        # Handle expires_at
        expires_at = request.POST.get('expires_at', '')
        if expires_at:
            from django.utils import timezone
            from datetime import datetime
            try:
                link.expires_at = datetime.fromisoformat(expires_at)
            except ValueError:
                pass
        else:
            link.expires_at = None

        # Handle expires_after_downloads
        expires_after = request.POST.get('expires_after_downloads', '')
        if expires_after:
            try:
                link.expires_after_downloads = int(expires_after)
            except ValueError:
                pass
        else:
            link.expires_after_downloads = None

        link.save()

        from django.contrib import messages
        messages.success(request, 'Link-Einstellungen gespeichert.')

        return redirect('sharing:link_settings', link_id=link.id)


class DeletePublicLinkView(LoginRequiredMixin, DeleteView):
    """Delete public link"""
    model = PublicLink
    success_url = reverse_lazy('sharing:links_list')
    pk_url_kwarg = 'link_id'

    def get_queryset(self):
        return PublicLink.objects.filter(owner=self.request.user)


class GroupsListView(LoginRequiredMixin, ListView):
    """List groups"""
    template_name = 'sharing/groups_list.html'
    context_object_name = 'groups'

    def get_company(self):
        return _url_company(self.request.user, self.kwargs['company_slug'])

    def get_queryset(self):
        return _group_queryset(self.request.user).filter(company=self.get_company()).select_related('company', 'department', 'owner')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company'] = self.get_company()
        return context


class GroupCompanyRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        company = _user_company(request.user)
        if not company:
            return render(request, '403.html', {
                'error_message': 'Dein Nutzer ist noch keiner Firma zugeordnet.',
            }, status=403)
        return redirect('sharing:groups_list', company_slug=company.slug)


class CreateGroupView(LoginRequiredMixin, CreateView):
    """Create sharing group"""
    template_name = 'sharing/create_group.html'
    model = GroupShare
    fields = ['company', 'department', 'group_name', 'members', 'background_image', 'background_video']
    success_url = reverse_lazy('sharing:groups_root')

    def get_company(self):
        return _url_company(self.request.user, self.kwargs['company_slug'])

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('sharing.create_groupshare'):
            from django.shortcuts import render as _r
            return _r(request, '403.html', {
                'error_message': 'Du hast keine Berechtigung, Team-Sites zu erstellen.',
            }, status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        site_folder = StorageFolder.objects.create(
            owner=self.request.user,
            parent=None,
            name=form.cleaned_data['group_name'],
            description=f"Dokumentbibliothek fuer Team Site {form.cleaned_data['group_name']}",
        )

        form.instance.owner = self.request.user
        form.instance.company = self.get_company()
        form.instance.content_type = ContentType.objects.get_for_model(StorageFolder)
        form.instance.object_id = site_folder.id
        form.instance.permission = 'admin'

        response = super().form_valid(form)
        self.object.members.add(self.request.user)
        return response

    def get_success_url(self):
        return reverse_lazy('sharing:group_detail', kwargs={'company_slug': self.object.company.slug, 'group_id': self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company'] = self.get_company()
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company = self.get_company()
        form.fields['company'].queryset = form.fields['company'].queryset.filter(is_active=True).order_by('name')
        form.fields['company'].queryset = form.fields['company'].queryset.filter(pk=company.pk)
        form.fields['company'].initial = company.pk
        form.fields['department'].queryset = form.fields['department'].queryset.filter(company=company).order_by('name')
        form.fields['members'].queryset = form.fields['members'].queryset.filter(profile__company=company, is_active=True)
        return form


class GroupDetailView(LoginRequiredMixin, DetailView):
    """Detailed Team Site view."""
    template_name = 'sharing/group_detail.html'
    context_object_name = 'group'
    pk_url_kwarg = 'group_id'
    model = GroupShare

    def get_company(self):
        return _url_company(self.request.user, self.kwargs['company_slug'])

    def get_queryset(self):
        return _group_queryset(self.request.user).filter(company=self.get_company())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.object
        library = group.content_object if isinstance(group.content_object, StorageFolder) else None

        context['library'] = library
        context['library_files'] = library.files.order_by('-updated_at')[:8] if library else []
        context['subfolders'] = library.subfolders.order_by('name')[:8] if library else []
        context['site_news'] = group.news_items.filter(
            is_published=True
        ).filter(
            Q(publish_at__isnull=True) | Q(publish_at__lte=timezone.now())
        ).order_by('-is_pinned', '-publish_at', '-created_at')[:5]
        context['background_image_url'] = group.background_image.url if group.background_image else ''
        context['background_video_url'] = group.background_video.url if group.background_video else ''
        context['can_manage_site'] = group.user_can_manage(self.request.user)
        context['company'] = group.company
        context['department'] = group.department
        context['site_webparts'] = [
            {'title': 'News', 'icon': 'bi-megaphone', 'description': 'Aktuelle Meldungen und Team-Updates.'},
            {'title': 'Dokumentbibliothek', 'icon': 'bi-folder2-open', 'description': 'Dateien, Versionen und Ordner der Team Site.'},
            {'title': 'Mitglieder', 'icon': 'bi-people', 'description': 'Owner, Team und Rollen im Bereich.'},
            {'title': 'Schnelllinks', 'icon': 'bi-link-45deg', 'description': 'Wichtige Ziele fuer Projekte und Abteilungen.'},
        ]
        context['quick_links'] = [
            {'label': 'Dateibibliothek oeffnen', 'url': reverse_lazy('storage:folder', kwargs={'folder_id': library.id}) if library else reverse_lazy('storage:file_list')},
            {'label': 'Geteilte Inhalte', 'url': reverse_lazy('sharing:shared_with_me')},
        ]
        mysite_url = get_optional_plugin_app_url('mysite', request=self.request)
        if mysite_url:
            context['quick_links'].append({'label': 'MySite Hub', 'url': mysite_url})
        return context


class GroupUpdateView(LoginRequiredMixin, UpdateView):
    """Edit Team Site metadata."""
    model = GroupShare
    template_name = 'sharing/group_edit.html'
    fields = ['company', 'department', 'group_name', 'members', 'team_leaders', 'background_image', 'background_video']
    pk_url_kwarg = 'group_id'

    def get_company(self):
        return _url_company(self.request.user, self.kwargs['company_slug'])

    def get_queryset(self):
        return _group_queryset(self.request.user).filter(company=self.get_company())

    def get_success_url(self):
        return reverse_lazy('sharing:group_detail', kwargs={'company_slug': self.object.company.slug, 'group_id': self.object.id})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company = self.object.company or self.get_company()
        form.fields['company'].queryset = form.fields['company'].queryset.filter(is_active=True).order_by('name')
        if company:
            form.fields['company'].queryset = form.fields['company'].queryset.filter(pk=company.pk)
            form.fields['department'].queryset = form.fields['department'].queryset.filter(company=company).order_by('name')
            user_qs = User.objects.filter(profile__company=company, is_active=True).order_by('last_name', 'username')
            form.fields['members'].queryset = user_qs
            form.fields['team_leaders'].queryset = user_qs
        return form


class TeamSiteManageMixin(LoginRequiredMixin):
    def get_company(self):
        return _url_company(self.request.user, self.kwargs['company_slug'])

    def get_group(self):
        """Gibt die Team-Site zurueck, wenn der Nutzer in der Firma Zugriff hat."""
        return get_object_or_404(
            _group_queryset(self.request.user).filter(company=self.get_company()),
            id=self.kwargs['group_id'],
        )

    def _permission_denied(self, request, group):
        """Zeigt eine verstaendliche 403-Seite statt eines stummen 404."""
        from django.shortcuts import render as _render
        return _render(request, '403.html', {
            'error_message': (
                f'Du bist Mitglied von "{group.group_name}", '
                f'aber nur Team-Leader oder der Besitzer darf hier Aenderungen vornehmen.'
            ),
            'back_url': reverse_lazy('sharing:group_detail', kwargs={'company_slug': group.company.slug, 'group_id': group.pk}),
            'back_label': f'Zurueck zu {group.group_name}',
        }, status=403)

    def dispatch(self, request, *args, **kwargs):
        group = self.get_group()
        if request.method.lower() in {'post', 'put', 'patch', 'delete'} or getattr(self, 'require_manage_access', False):
            if not group.user_can_manage(request.user):
                return self._permission_denied(request, group)
        self.group = group
        return super().dispatch(request, *args, **kwargs)


class TeamSiteNewsListView(TeamSiteManageMixin, ListView):
    template_name = 'sharing/team_news_list.html'
    context_object_name = 'news_items'

    def get_queryset(self):
        queryset = self.group.news_items.all()
        if not self.group.user_can_manage(self.request.user):
            queryset = queryset.filter(is_published=True).filter(
                Q(publish_at__isnull=True) | Q(publish_at__lte=timezone.now())
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = self.group
        context['company'] = self.group.company
        context['can_manage_site'] = self.group.user_can_manage(self.request.user)
        return context


class TeamSiteNewsDetailView(TeamSiteManageMixin, DetailView):
    template_name = 'sharing/team_news_detail.html'
    context_object_name = 'news'
    pk_url_kwarg = 'news_id'
    model = TeamSiteNews

    def get_queryset(self):
        queryset = TeamSiteNews.objects.filter(group=self.group)
        if not self.group.user_can_manage(self.request.user):
            queryset = queryset.filter(is_published=True).filter(
                Q(publish_at__isnull=True) | Q(publish_at__lte=timezone.now())
            )
        return queryset

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        TeamSiteNews.objects.filter(pk=obj.pk).update(view_count=models.F('view_count') + 1)
        obj.refresh_from_db(fields=['view_count'])
        return obj

    def get_context_data(self, **kwargs):
        from django.contrib.contenttypes.models import ContentType as CT
        from news.models import Comment, Reaction

        context = super().get_context_data(**kwargs)
        context['group'] = self.group
        context['company'] = self.group.company
        context['can_manage_site'] = self.group.user_can_manage(self.request.user)

        news_obj = self.object
        ct = CT.objects.get_for_model(TeamSiteNews)

        comments = Comment.objects.filter(
            content_type=ct,
            object_id=news_obj.pk,
            parent__isnull=True,
            is_deleted=False,
        ).select_related('author').prefetch_related('replies__author')
        context['comments'] = comments

        reactions = Reaction.objects.filter(content_type=ct, object_id=news_obj.pk)
        context['reaction_like_count'] = reactions.filter(reaction='like').count()
        context['reaction_heart_count'] = reactions.filter(reaction='heart').count()

        user_reaction = None
        try:
            user_reaction = Reaction.objects.get(
                content_type=ct,
                object_id=news_obj.pk,
                user=self.request.user,
            ).reaction
        except Reaction.DoesNotExist:
            pass
        context['user_reaction'] = user_reaction
        return context


class TeamSiteNewsCreateView(TeamSiteManageMixin, CreateView):
    template_name = 'sharing/team_news_form.html'
    model = TeamSiteNews
    form_class = TeamSiteNewsForm
    require_manage_access = True

    def form_valid(self, form):
        form.instance.group = self.group
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = self.group
        context['company'] = self.group.company
        context['form_mode'] = 'create'
        return context

    def get_success_url(self):
        return reverse_lazy('sharing:team_news_detail', kwargs={'company_slug': self.group.company.slug, 'group_id': self.group.id, 'news_id': self.object.id})


class TeamSiteNewsUpdateView(TeamSiteManageMixin, UpdateView):
    template_name = 'sharing/team_news_form.html'
    model = TeamSiteNews
    form_class = TeamSiteNewsForm
    pk_url_kwarg = 'news_id'
    require_manage_access = True

    def get_queryset(self):
        return TeamSiteNews.objects.filter(group=self.group)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = self.group
        context['company'] = self.group.company
        context['form_mode'] = 'edit'
        return context

    def get_success_url(self):
        return reverse_lazy('sharing:team_news_detail', kwargs={'company_slug': self.group.company.slug, 'group_id': self.group.id, 'news_id': self.object.id})


class GroupShareView(LoginRequiredMixin, CreateView):
    """Share with group"""
    template_name = 'sharing/group_share.html'
    model = GroupShare
    fields = ['permission']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = get_object_or_404(
            _group_queryset(self.request.user).filter(company=_url_company(self.request.user, self.kwargs['company_slug'])),
            id=self.kwargs.get('group_id'),
        )
        context['company'] = context['group'].company
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


class CreatePublicLinkView(LoginRequiredMixin, CreateView):
    """Create a public link for a file or folder"""
    model = PublicLink
    template_name = 'sharing/create_link.html'
    fields = ['title', 'description', 'permission', 'expires_at', 'expires_after_downloads', 'allow_download']

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
            context['content_type'] = 'file'
        elif content_type == 'folder':
            context['object'] = get_object_or_404(
                StorageFolder,
                id=object_id,
                owner=self.request.user
            )
            context['content_type'] = 'folder'

        return context

    def form_valid(self, form):
        from django.contrib.contenttypes.models import ContentType as CT

        content_type = self.kwargs.get('content_type')
        object_id = self.kwargs.get('object_id')

        form.instance.owner = self.request.user

        if content_type == 'file':
            ct = CT.objects.get_for_model(StorageFile)
            obj = get_object_or_404(StorageFile, id=object_id, owner=self.request.user)
        else:
            ct = CT.objects.get_for_model(StorageFolder)
            obj = get_object_or_404(StorageFolder, id=object_id, owner=self.request.user)

        form.instance.content_type = ct
        form.instance.object_id = object_id

        # Log the action
        ShareLog.objects.create(
            user=self.request.user,
            action='created',
            content_type=ct,
            object_id=object_id,
            description=f"Public link created for {obj}"
        )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('sharing:link_created', kwargs={'pk': self.object.pk})


class LinkCreatedView(LoginRequiredMixin, DetailView):
    """Show the created link with copy functionality"""
    model = PublicLink
    template_name = 'sharing/link_created.html'
    context_object_name = 'link'

    def get_queryset(self):
        return PublicLink.objects.filter(owner=self.request.user)
