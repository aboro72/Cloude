"""
REST API Views for CloudService.
Django REST Framework with comprehensive CRUD operations.
"""

from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum
from django.http import FileResponse
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from core.mongo_audit import get_user_activity_entries, log_search_event

from core.models import StorageFile, StorageFolder, FileVersion, ActivityLog, Notification
from accounts.models import UserProfile
from sharing.models import UserShare, PublicLink, SharePermission
from storage.models import StorageStats
from api.serializers import (
    StorageFileSerializer, StorageFileDetailSerializer, StorageFolderSerializer,
    FileVersionSerializer, UserShareSerializer, PublicLinkSerializer,
    ActivityLogSerializer, NotificationSerializer, UserSerializer,
    StorageStatsSerializer, FileUploadSerializer, BulkDeleteSerializer,
    SearchResultSerializer,
    DepartmentSerializer, DepartmentMemberSerializer,
    GroupShareSerializer,
    TaskBoardSerializer, TaskSerializer,
    NewsCategorySerializer, NewsArticleSerializer,
)
from api.permissions import IsFileOwnerOrShared, IsPublicLinkValid
import logging

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Custom pagination for API"""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class StorageFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for file operations.
    Supports CRUD operations with permissions.
    """
    serializer_class = StorageFileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'size', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get files for current user"""
        user = self.request.user
        return StorageFile.objects.filter(
            Q(owner=user) | Q(usershare__shared_with=user)
        ).distinct()

    def get_serializer_class(self):
        """Use detailed serializer for retrieve"""
        if self.action == 'retrieve':
            return StorageFileDetailSerializer
        return StorageFileSerializer

    def perform_create(self, serializer):
        """Create file with current user as owner"""
        serializer.save(owner=self.request.user)
        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            activity_type='upload',
            file=serializer.instance,
            description=f"Uploaded file: {serializer.instance.name}",
            ip_address=self.get_client_ip()
        )

    def perform_update(self, serializer):
        """Update file"""
        serializer.save()
        ActivityLog.objects.create(
            user=self.request.user,
            activity_type='rename',
            file=serializer.instance,
            description=f"Updated file: {serializer.instance.name}",
            ip_address=self.get_client_ip()
        )

    def perform_destroy(self, instance):
        """Delete file"""
        ActivityLog.objects.create(
            user=self.request.user,
            activity_type='delete',
            file=instance,
            description=f"Deleted file: {instance.name}",
            ip_address=self.get_client_ip()
        )
        instance.delete()

    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """Download file"""
        file_obj = self.get_object()

        # Check permissions
        if file_obj.owner != request.user:
            share = UserShare.objects.filter(
                shared_with=request.user,
                object_id=file_obj.id,
                content_type__model='storagefile',
                is_active=True
            ).first()
            if not share or not share.can_download():
                raise PermissionDenied("You don't have permission to download this file")

        file_obj.increment_download_count()
        ActivityLog.objects.create(
            user=request.user,
            activity_type='download',
            file=file_obj,
            description=f"Downloaded: {file_obj.name}",
            ip_address=self.get_client_ip()
        )

        response = FileResponse(file_obj.file.open('rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'
        return response

    @action(detail=True, methods=['post'])
    def star(self, request, pk=None):
        """Star/unstar file"""
        file_obj = self.get_object()
        file_obj.is_starred = not file_obj.is_starred
        file_obj.save()
        return Response({
            'is_starred': file_obj.is_starred
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create duplicate of file"""
        original = self.get_object()

        # Create new file instance
        import shutil
        import os

        duplicate = StorageFile.objects.create(
            owner=request.user,
            folder=original.folder,
            name=f"{original.name} (copy)",
            size=original.size
        )

        # Copy file content
        duplicate.file.save(
            os.path.basename(original.file.name),
            original.file.open('rb'),
            save=True
        )

        serializer = self.get_serializer(duplicate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class StorageFolderViewSet(viewsets.ModelViewSet):
    """ViewSet for folder operations"""
    serializer_class = StorageFolderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get folders for current user"""
        return StorageFolder.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """Create folder with current user as owner"""
        serializer.save(owner=self.request.user)
        ActivityLog.objects.create(
            user=self.request.user,
            activity_type='create_folder',
            folder=serializer.instance,
            description=f"Created folder: {serializer.instance.name}"
        )

    @action(detail=True, methods=['get'])
    def contents(self, request, pk=None):
        """Get folder contents"""
        folder = self.get_object()

        subfolders = folder.subfolders.all()
        files = folder.files.all()

        folder_serializer = StorageFolderSerializer(subfolders, many=True)
        file_serializer = StorageFileSerializer(files, many=True)

        return Response({
            'folders': folder_serializer.data,
            'files': file_serializer.data
        })


class FileVersionsView(generics.ListAPIView):
    """Get file versions"""
    serializer_class = FileVersionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Get versions for specific file"""
        file_id = self.kwargs.get('file_id')
        return FileVersion.objects.filter(file_id=file_id).order_by('-version_number')


class RestoreFileVersionView(generics.GenericAPIView):
    """Restore file to previous version"""
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        """Restore file version"""
        file_obj = get_object_or_404(StorageFile, id=file_id, owner=request.user)
        version_id = request.data.get('version_id')

        version = get_object_or_404(FileVersion, id=version_id, file=file_obj)

        # Create new version with restored content
        new_version_number = file_obj.version_count + 1

        FileVersion.objects.create(
            file=file_obj,
            version_number=new_version_number,
            file_data=version.file_data,
            file_hash=version.file_hash,
            size=version.size,
            change_description=f"Restored from version {version.version_number}",
            is_current=True
        )

        # Update current file
        file_obj.version_count = new_version_number
        file_obj.save()

        return Response({
            'message': 'File restored successfully',
            'version_number': new_version_number
        })


class UserShareViewSet(viewsets.ModelViewSet):
    """ViewSet for user shares"""
    serializer_class = UserShareSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Get shares for current user"""
        user = self.request.user
        return UserShare.objects.filter(
            Q(owner=user) | Q(shared_with=user)
        ).distinct()

    def perform_create(self, serializer):
        """Create share with current user as owner"""
        serializer.save(owner=self.request.user)

        # Send notification to shared user
        Notification.create_notification(
            user=serializer.instance.shared_with,
            notification_type='share',
            title='File Shared',
            message=f"{self.request.user.username} shared a file with you",
            expires_hours=72
        )

    @action(detail=True, methods=['post'])
    def update_permission(self, request, pk=None):
        """Update share permission"""
        share = self.get_object()
        if share.owner != request.user:
            raise PermissionDenied("You don't have permission to update this share")

        permission = request.data.get('permission')
        share.permission = permission
        share.save()

        return Response(UserShareSerializer(share).data)


class PublicLinkViewSet(viewsets.ModelViewSet):
    """ViewSet for public links"""
    serializer_class = PublicLinkSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    lookup_field = 'token'

    def get_queryset(self):
        """Get public links for current user"""
        return PublicLink.objects.filter(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def set_password(self, request, token=None):
        """Set password for public link"""
        link = self.get_object()
        password = request.data.get('password')

        if password:
            link.set_password(password)
            link.save()

        return Response({'message': 'Password updated'})

    @action(detail=True, methods=['post'])
    def disable(self, request, token=None):
        """Disable public link"""
        link = self.get_object()
        link.is_active = False
        link.save()
        return Response({'message': 'Link disabled'})


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for activity logs"""
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering = ['-created_at']
    search_fields = ['description', 'activity_type']

    def get_queryset(self):
        """Get activities for current user"""
        mongo_entries = get_user_activity_entries(self.request.user, limit=500)
        if mongo_entries:
            return mongo_entries
        return ActivityLog.objects.filter(user=self.request.user)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for users"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Get users (limited view for privacy)"""
        # Only return current user
        return self.request.user.__class__.objects.filter(id=self.request.user.id)


class StorageStatsView(generics.RetrieveAPIView):
    """Get storage statistics"""
    serializer_class = StorageStatsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Get or create storage stats for current user"""
        stats, _ = StorageStats.objects.get_or_create(user=self.request.user)
        return stats


class StorageQuotaView(generics.GenericAPIView):
    """Get storage quota information"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get quota details"""
        profile = request.user.profile

        return Response({
            'quota': profile.storage_quota,
            'used': profile.get_storage_used(),
            'remaining': profile.get_storage_remaining(),
            'percentage_used': profile.get_storage_used_percentage(),
            'is_full': profile.is_storage_full(),
            'is_warning': profile.is_storage_warning()
        })


class FileDownloadAPIView(generics.GenericAPIView):
    """Download file via API"""
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        """Download file"""
        file_obj = get_object_or_404(StorageFile, id=file_id)

        if file_obj.owner != request.user:
            raise PermissionDenied("You don't have permission to download this file")

        file_obj.increment_download_count()

        response = FileResponse(file_obj.file.open('rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'
        return response


class SearchAPIView(generics.GenericAPIView):
    """Search files and folders"""
    permission_classes = [IsAuthenticated]
    serializer_class = SearchResultSerializer
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Search"""
        query = request.query_params.get('q', '')

        if not query:
            return Response([])

        files = StorageFile.objects.filter(
            owner=request.user,
            name__icontains=query
        )[:10]

        folders = StorageFolder.objects.filter(
            owner=request.user,
            name__icontains=query
        )[:10]

        results = []
        for file in files:
            results.append({
                'type': 'file',
                'id': file.id,
                'name': file.name
            })

        for folder in folders:
            results.append({
                'type': 'folder',
                'id': folder.id,
                'name': folder.name
            })

        try:
            counts = {}
            for item in results:
                counts[item['type']] = counts.get(item['type'], 0) + 1
            log_search_event(
                user=request.user,
                query=query,
                source='api',
                results=counts,
            )
        except Exception:
            pass

        return Response(results)


class NotificationListView(generics.ListAPIView):
    """Get notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Get notifications for current user"""
        return Notification.objects.filter(user=self.request.user)


class MarkNotificationReadView(generics.GenericAPIView):
    """Mark notification as read"""
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        """Mark as read"""
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()

        return Response({'message': 'Marked as read'})


class UpdateSharePermissionView(generics.GenericAPIView):
    """Update share permission"""
    permission_classes = [IsAuthenticated]

    def post(self, request, share_id):
        """Update permission"""
        share = get_object_or_404(UserShare, id=share_id, owner=request.user)
        permission = request.data.get('permission')

        share.permission = permission
        share.save()

        return Response(UserShareSerializer(share).data)


class SetPublicLinkPasswordView(generics.GenericAPIView):
    """Set password for public link"""
    permission_classes = [IsAuthenticated]

    def post(self, request, link_id):
        """Set password"""
        link = get_object_or_404(PublicLink, id=link_id, owner=request.user)
        password = request.data.get('password')

        if password:
            link.set_password(password)
            link.save()

        return Response({'message': 'Password updated'})


# Plugin Management Views
class PluginActivateView(APIView):
    """Activate a plugin"""
    permission_classes = [IsAdminUser]

    def post(self, request, plugin_id):
        """Activate plugin"""
        try:
            from plugins.models import Plugin
            from plugins.loader import PluginLoader
            from django.contrib import messages

            plugin = get_object_or_404(Plugin, id=plugin_id)
            loader = PluginLoader()
            loader.load_plugin(str(plugin_id))

            # Redirect back with success message
            from django.shortcuts import redirect
            messages.success(request, f'✅ Plugin "{plugin.name}" activated successfully')
            return redirect('core:settings')

        except Exception as e:
            from django.shortcuts import redirect
            from django.contrib import messages
            messages.error(request, f'❌ Activation failed: {str(e)}')
            return redirect('core:settings')


class PluginDeactivateView(APIView):
    """Deactivate a plugin"""
    permission_classes = [IsAdminUser]

    def post(self, request, plugin_id):
        """Deactivate plugin"""
        try:
            from plugins.models import Plugin
            from plugins.loader import PluginLoader
            from django.contrib import messages

            plugin = get_object_or_404(Plugin, id=plugin_id)
            loader = PluginLoader()
            loader.unload_plugin(str(plugin_id))

            # Redirect back with success message
            from django.shortcuts import redirect
            messages.success(request, f'✅ Plugin "{plugin.name}" deactivated successfully')
            return redirect('core:settings')

        except Exception as e:
            from django.shortcuts import redirect
            from django.contrib import messages
            messages.error(request, f'❌ Deactivation failed: {str(e)}')
            return redirect('core:settings')


class PluginUninstallView(APIView):
    """Fully uninstall a plugin (deactivate + delete files + delete DB record)"""
    permission_classes = [IsAdminUser]

    def post(self, request, plugin_id):
        """Uninstall plugin"""
        try:
            from plugins.models import Plugin
            from plugins.loader import PluginLoader
            from django.contrib import messages
            from django.shortcuts import redirect

            plugin = get_object_or_404(Plugin, id=plugin_id)
            plugin_name = plugin.name
            loader = PluginLoader()
            loader.uninstall_plugin(str(plugin_id))

            messages.success(request, f'✅ Plugin "{plugin_name}" wurde deinstalliert')
            return redirect('core:settings')

        except Exception as e:
            from django.shortcuts import redirect
            from django.contrib import messages
            messages.error(request, f'❌ Deinstallation fehlgeschlagen: {str(e)}')
            return redirect('core:settings')


class PluginDiscoverView(APIView):
    """Discover plugins from filesystem"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        """Scan plugins directory and register new plugins"""
        try:
            from plugins.loader import PluginLoader
            from django.contrib import messages
            from django.shortcuts import redirect

            loader = PluginLoader()
            discovered = loader.discover_plugins()

            new_count = sum(1 for d in discovered if d['created'])

            if new_count > 0:
                messages.success(request, f'✅ {new_count} neue Plugin(s) entdeckt!')
            else:
                messages.info(request, 'Keine neuen Plugins gefunden.')

            return redirect('core:settings')

        except Exception as e:
            from django.shortcuts import redirect
            from django.contrib import messages
            messages.error(request, f'❌ Fehler: {str(e)}')
            return redirect('core:settings')


class PluginSettingsView(APIView):
    """View and update plugin settings"""
    permission_classes = [IsAdminUser]

    def get(self, request, plugin_id):
        """Show plugin settings form"""
        from django.shortcuts import render
        from plugins.models import Plugin

        plugin = get_object_or_404(Plugin, id=plugin_id)

        # Prepare fields with current values
        fields = []
        for key, field_def in plugin.settings_schema.items():
            field = {
                'key': key,
                'value': plugin.settings.get(key, field_def.get('default', '')),
                **field_def
            }
            fields.append(field)

        return render(request, 'plugins/settings.html', {
            'plugin': plugin,
            'fields': fields,
        })

    def post(self, request, plugin_id):
        """Save plugin settings"""
        from django.shortcuts import redirect
        from django.contrib import messages
        from plugins.models import Plugin

        plugin = get_object_or_404(Plugin, id=plugin_id)

        try:
            # Get settings from form
            new_settings = {}
            for key, field_def in plugin.settings_schema.items():
                value = request.POST.get(key, '')

                # Type conversion based on schema
                field_type = field_def.get('type', 'text')
                if field_type == 'number':
                    value = float(value) if value else 0
                elif field_type == 'boolean':
                    value = key in request.POST
                elif field_type == 'integer':
                    value = int(value) if value else 0

                new_settings[key] = value

            # Save settings
            plugin.settings = new_settings
            plugin.save()

            messages.success(request, f'✅ Einstellungen für "{plugin.name}" gespeichert!')

        except Exception as e:
            messages.error(request, f'❌ Fehler beim Speichern: {str(e)}')

        return redirect('api:plugin_settings', plugin_id=plugin_id)


# ── Departments ───────────────────────────────────────────────────────────────

class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve departments.
    All authenticated users can read; creating/updating requires
    the `departments.create_department` or `departments.manage_any_department` permission.
    """
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        from departments.models import Department
        qs = Department.objects.select_related('head', 'company').all()
        company = getattr(getattr(self.request.user, 'profile', None), 'company', None)
        if company:
            qs = qs.filter(company=company)
        return qs

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """List members of a department."""
        from departments.models import DepartmentMembership
        dept = self.get_object()
        memberships = DepartmentMembership.objects.filter(
            department=dept
        ).select_related('user').order_by('role', 'user__last_name')
        serializer = DepartmentMemberSerializer(memberships, many=True)
        return Response(serializer.data)


# ── Team Sites (GroupShare) ───────────────────────────────────────────────────

class GroupShareViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve Team Sites (GroupShare).
    Returns only sites the authenticated user is a member or owner of.
    """
    serializer_class = GroupShareSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['group_name']
    ordering = ['group_name']

    def get_queryset(self):
        from sharing.models import GroupShare
        user = self.request.user
        return GroupShare.objects.filter(
            Q(owner=user) | Q(members=user)
        ).distinct().select_related('owner', 'company', 'department')


# ── Kanban Boards & Tasks ─────────────────────────────────────────────────────

class TaskBoardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve Task Boards accessible to the current user
    (personal, team-site, or department boards).
    """
    serializer_class = TaskBoardSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title']
    ordering = ['title']

    def get_queryset(self):
        from tasks_board.models import TaskBoard
        from departments.models import DepartmentMembership
        user = self.request.user
        personal_ids = TaskBoard.objects.filter(owner=user).values_list('id', flat=True)
        team_ids = TaskBoard.objects.filter(
            team_site__isnull=False,
            team_site__members=user
        ).values_list('id', flat=True)
        dept_ids_user = list(
            DepartmentMembership.objects.filter(user=user).values_list('department_id', flat=True)
        )
        headed = list(user.headed_departments.values_list('pk', flat=True))
        all_dept_ids = list(set(dept_ids_user) | set(headed))
        dept_board_ids = TaskBoard.objects.filter(
            department_id__in=all_dept_ids
        ).values_list('id', flat=True)
        all_ids = set(list(personal_ids) + list(team_ids) + list(dept_board_ids))
        return TaskBoard.objects.filter(pk__in=all_ids).select_related(
            'owner', 'department', 'team_site'
        )

    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        """List tasks for this board (respects member/manager visibility)."""
        from tasks_board.views import _board_access, _can_manage
        board = self.get_object()
        if not _board_access(board, request.user):
            return Response({'detail': 'Kein Zugriff'}, status=403)
        can_manage = _can_manage(board, request.user)
        qs = board.tasks.select_related('assigned_to', 'created_by').order_by('status', 'order')
        if not can_manage:
            qs = qs.filter(Q(assigned_to=request.user) | Q(assigned_to__isnull=True))
        serializer = TaskSerializer(qs, many=True)
        return Response(serializer.data)


class TaskViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve Tasks assigned to or created by the current user.
    """
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'status', 'created_at']
    ordering = ['status', 'order']

    def get_queryset(self):
        from tasks_board.models import Task
        user = self.request.user
        return Task.objects.filter(
            Q(assigned_to=user) | Q(created_by=user)
        ).distinct().select_related('board', 'assigned_to', 'created_by')


# ── News ──────────────────────────────────────────────────────────────────────

class NewsCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve News Categories."""
    serializer_class = NewsCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from news.models import NewsCategory
        return NewsCategory.objects.all()


class NewsArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve published News Articles.
    Staff with `news.change_newsarticle` permission also see unpublished drafts.
    """
    serializer_class = NewsArticleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'summary', 'tags']
    ordering_fields = ['publish_at', 'created_at', 'view_count']
    ordering = ['-publish_at', '-created_at']

    def get_queryset(self):
        from news.models import NewsArticle
        qs = NewsArticle.objects.select_related('author', 'category')
        if not self.request.user.has_perm('news.change_newsarticle'):
            qs = qs.filter(is_published=True)
        return qs
