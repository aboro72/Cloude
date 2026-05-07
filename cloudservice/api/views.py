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
    ChatRoomSerializer, ChatRoomDetailSerializer,
    ChatMessageSerializer, ChatMembershipSerializer, ChatInviteSerializer,
    MeetingSerializer,
)
from api.permissions import IsFileOwnerOrShared, IsPublicLinkValid, IsChatRoomMember, IsChatMessageAuthor
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
        settings_schema = plugin.settings_schema or {}
        current_settings = plugin.settings or {}
        for key, field_def in settings_schema.items():
            field = {
                'key': key,
                'value': current_settings.get(key, field_def.get('default', '')),
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
            settings_schema = plugin.settings_schema or {}
            for key, field_def in settings_schema.items():
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
        return Department.objects.select_related('head').all()

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
        ).distinct().select_related('owner')


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

# ── Messenger ─────────────────────────────────────────────────────────────────

class ChatRoomViewSet(viewsets.ModelViewSet):
    """
    CRUD für Chat-Räume (Kanäle, Gruppen, Direktnachrichten).

    - GET  /messenger/rooms/           → eigene Räume (Mitglied oder Ersteller)
    - POST /messenger/rooms/           → neuen Kanal/Gruppe anlegen
    - GET  /messenger/rooms/{id}/      → Raumdetail inkl. Mitgliederliste
    - POST /messenger/rooms/{id}/join/ → öffentlichem Raum beitreten
    - POST /messenger/rooms/{id}/leave/→ Raum verlassen
    - POST /messenger/rooms/{id}/mark_read/ → alle Nachrichten als gelesen markieren
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatRoomDetailSerializer
        return ChatRoomSerializer

    def get_queryset(self):
        from messenger.models import ChatRoom
        user = self.request.user
        return (
            ChatRoom.objects
            .filter(members=user, is_archived=False)
            .distinct()
            .select_related('created_by')
            .prefetch_related('memberships__user')
        )

    def perform_create(self, serializer):
        from messenger.models import ChatRoom, ChatMembership
        room = serializer.save(
            company=self.request.user.profile.company,
            created_by=self.request.user,
        )
        ChatMembership.objects.create(room=room, user=self.request.user, role='owner')

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Öffentlichem Raum beitreten."""
        from messenger.models import ChatRoom, ChatMembership
        room = get_object_or_404(ChatRoom, pk=pk, is_archived=False)
        if room.is_private:
            return Response({'detail': 'Dieser Raum ist privat.'}, status=status.HTTP_403_FORBIDDEN)
        membership, created = ChatMembership.objects.get_or_create(
            room=room, user=request.user, defaults={'role': 'member'}
        )
        return Response(
            {'detail': 'Beigetreten.' if created else 'Bereits Mitglied.'},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Raum verlassen."""
        from messenger.models import ChatMembership
        room = self.get_object()
        deleted, _ = ChatMembership.objects.filter(room=room, user=request.user).delete()
        if not deleted:
            return Response({'detail': 'Kein Mitglied.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Raum verlassen.'})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Letzten Lesezeitpunkt auf jetzt setzen."""
        from messenger.models import ChatMembership
        room = self.get_object()
        updated = ChatMembership.objects.filter(room=room, user=request.user).update(
            last_read_at=timezone.now()
        )
        if not updated:
            return Response({'detail': 'Kein Mitglied.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Als gelesen markiert.'})

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Mitgliederliste eines Raums."""
        room = self.get_object()
        memberships = room.memberships.select_related('user').order_by('role', 'user__username')
        return Response(ChatMembershipSerializer(memberships, many=True).data)


class ChatMessageViewSet(viewsets.ModelViewSet):
    """
    Nachrichten innerhalb eines Chat-Raums.

    URL-Parameter: room_pk (verschachtelt unter /messenger/rooms/{room_pk}/messages/)

    - GET    → Nachrichten-Liste (paginiert, älteste zuerst)
    - POST   → Neue Nachricht senden
    - PATCH  → Eigene Nachricht bearbeiten
    - DELETE → Eigene Nachricht soft-löschen
    - POST /messages/{id}/react/ → Emoji-Reaktion togglen
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['content']
    ordering = ['created_at']

    def _get_room(self):
        from messenger.models import ChatRoom, ChatMembership
        room_pk = self.kwargs.get('room_pk')
        room = get_object_or_404(ChatRoom, pk=room_pk, is_archived=False)
        if not ChatMembership.objects.filter(room=room, user=self.request.user).exists():
            raise PermissionDenied('Du bist kein Mitglied dieses Raums.')
        return room

    def get_queryset(self):
        from messenger.models import ChatMessage
        room = self._get_room()
        return (
            ChatMessage.objects
            .filter(room=room)
            .select_related('author', 'reply_to__author', 'storage_file')
            .order_by('created_at')
        )

    def get_serializer_class(self):
        return ChatMessageSerializer

    def perform_create(self, serializer):
        room = self._get_room()
        serializer.save(author=self.request.user, room=room)

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.author != self.request.user:
            raise PermissionDenied('Nur der Autor kann seine Nachricht bearbeiten.')
        serializer.save(is_edited=True, edited_at=timezone.now())

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied('Nur der Autor kann seine Nachricht löschen.')
        instance.soft_delete()

    @action(detail=True, methods=['post'])
    def react(self, request, room_pk=None, pk=None):
        """
        Emoji-Reaktion togglen.
        Body: {"emoji": "👍"}
        """
        message = self.get_object()
        emoji = request.data.get('emoji', '').strip()
        if not emoji:
            return Response({'detail': 'emoji fehlt.'}, status=status.HTTP_400_BAD_REQUEST)

        reactions = message.reactions or {}
        user_id = str(request.user.id)
        users = reactions.get(emoji, [])

        if user_id in users:
            users.remove(user_id)
            if not users:
                reactions.pop(emoji, None)
            else:
                reactions[emoji] = users
        else:
            users.append(user_id)
            reactions[emoji] = users

        message.reactions = reactions
        message.save(update_fields=['reactions'])
        return Response({'reactions': message.reactions})


class DirectMessageView(APIView):
    """
    Direktnachricht-Kanal mit einem anderen Nutzer starten oder abrufen.

    POST /messenger/direct/
    Body: {"user_id": 42}
    Gibt den bestehenden oder neu erstellten DM-Raum zurück.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from messenger.models import ChatRoom, ChatMembership
        from django.contrib.auth.models import User

        target_id = request.data.get('user_id')
        if not target_id:
            return Response({'detail': 'user_id fehlt.'}, status=status.HTTP_400_BAD_REQUEST)

        target = get_object_or_404(User, pk=target_id)
        if target == request.user:
            return Response({'detail': 'Kein DM mit sich selbst.'}, status=status.HTTP_400_BAD_REQUEST)

        company = request.user.profile.company

        # Vorhandenen DM-Raum suchen (beide Nutzer Mitglied, room_type=direct)
        existing = (
            ChatRoom.objects
            .filter(room_type='direct', company=company, members=request.user)
            .filter(members=target)
        ).first()

        if existing:
            return Response(ChatRoomDetailSerializer(existing, context={'request': request}).data)

        # Neuen DM-Raum erstellen
        dm_name = f'dm-{min(request.user.id, target.id)}-{max(request.user.id, target.id)}'
        room = ChatRoom.objects.create(
            company=company,
            room_type='direct',
            name=dm_name,
            is_private=True,
            created_by=request.user,
        )
        ChatMembership.objects.bulk_create([
            ChatMembership(room=room, user=request.user, role='member'),
            ChatMembership(room=room, user=target, role='member'),
        ])
        return Response(
            ChatRoomDetailSerializer(room, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class ChatInviteViewSet(viewsets.GenericViewSet):
    """
    Einladungslinks für Chat-Räume.

    - POST /messenger/rooms/{room_pk}/invites/       → Invite erstellen (Owner/Admin)
    - GET  /messenger/invites/{token}/               → Invite-Infos abrufen
    - POST /messenger/invites/{token}/accept/        → Invite annehmen, Raum beitreten
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ChatInviteSerializer

    def _get_room_as_manager(self, room_pk):
        from messenger.models import ChatRoom, ChatMembership
        room = get_object_or_404(ChatRoom, pk=room_pk)
        membership = ChatMembership.objects.filter(room=room, user=self.request.user).first()
        if not membership or membership.role not in ('owner', 'admin'):
            raise PermissionDenied('Nur Owner/Admin können Einladungen erstellen.')
        return room

    def create(self, request, room_pk=None):
        """Neuen Invite-Link anlegen."""
        from messenger.models import ChatInvite
        room = self._get_room_as_manager(room_pk)
        invite = ChatInvite.objects.create(
            room=room,
            invited_by=request.user,
            invited_email=request.data.get('invited_email', ''),
            max_uses=request.data.get('max_uses', 1),
            expires_at=request.data.get('expires_at'),
        )
        return Response(ChatInviteSerializer(invite).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        """Invite-Details per Token abrufen."""
        from messenger.models import ChatInvite
        invite = get_object_or_404(ChatInvite, token=pk)
        return Response(ChatInviteSerializer(invite).data)

    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        """Invite annehmen und dem Raum beitreten."""
        from messenger.models import ChatInvite, ChatMembership
        invite = get_object_or_404(ChatInvite, token=pk)
        if not invite.is_valid():
            return Response({'detail': 'Einladung ungültig oder abgelaufen.'}, status=status.HTTP_400_BAD_REQUEST)

        membership, created = ChatMembership.objects.get_or_create(
            room=invite.room, user=request.user, defaults={'role': 'member'}
        )
        invite.use_count += 1
        invite.save(update_fields=['use_count'])

        return Response(
            ChatRoomDetailSerializer(invite.room, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


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


# ── Meetings ──────────────────────────────────────────────────────────────────

class MeetingViewSet(viewsets.ModelViewSet):
    """
    Meetings im Firmen-Workspace.

    - GET    /meetings/                  → eigene Meetings (Organisator oder Eingeladener)
    - POST   /meetings/                  → Meeting planen
    - GET    /meetings/{id}/             → Meeting-Details
    - PATCH  /meetings/{id}/             → Titel/Beschreibung/Zeiten ändern (nur Organisator)
    - DELETE /meetings/{id}/             → Meeting löschen (nur Organisator/Admin)
    - POST   /meetings/{id}/start/       → Meeting starten (Raum wird erstellt)
    - POST   /meetings/{id}/end/         → Meeting beenden
    - POST   /meetings/{id}/cancel/      → Meeting absagen
    - GET    /meetings/{id}/join_url/    → Jitsi-JWT-Token + Join-URL abrufen
    - GET    /meetings/?status=planned   → nach Status filtern
    """
    serializer_class = MeetingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['scheduled_start', 'created_at', 'status']
    ordering = ['-created_at']

    def _get_company(self):
        profile = getattr(self.request.user, 'profile', None)
        if profile and profile.company:
            return profile.company
        if self.request.user.is_superuser:
            from accounts.models import Company
            return Company.objects.first()
        return None

    def get_queryset(self):
        from jitsi.models import Meeting
        company = self._get_company()
        if not company:
            return Meeting.objects.none()

        qs = Meeting.objects.filter(company=company).filter(
            Q(organizer=self.request.user) | Q(invitees=self.request.user)
        ).distinct().prefetch_related('invitees').select_related('organizer')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs

    def perform_create(self, serializer):
        from jitsi.models import Meeting
        company = self._get_company()
        if not company:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Kein Firmen-Workspace gefunden.')

        invitee_ids = self.request.data.get('invitee_ids', [])
        meeting = serializer.save(
            company=company,
            organizer=self.request.user,
            status=Meeting.STATUS_PLANNED,
        )
        if invitee_ids:
            from django.contrib.auth.models import User
            valid = User.objects.filter(
                pk__in=invitee_ids, is_active=True, profile__company=company
            )
            meeting.invitees.set(valid)

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.organizer != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied('Nur der Organisator kann das Meeting bearbeiten.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.organizer != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied('Nur der Organisator kann das Meeting löschen.')
        instance.delete()

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Meeting starten — generiert den Jitsi-Raumnamen."""
        meeting = self.get_object()
        if not meeting.can_be_started_by(request.user):
            return Response(
                {'detail': 'Meeting kann nicht gestartet werden.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        meeting.start()
        return Response(MeetingSerializer(meeting).data)

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """Meeting beenden."""
        meeting = self.get_object()
        if not meeting.can_be_ended_by(request.user):
            return Response(
                {'detail': 'Meeting kann nicht beendet werden.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        meeting.end()
        return Response(MeetingSerializer(meeting).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Meeting absagen."""
        meeting = self.get_object()
        if not meeting.can_be_cancelled_by(request.user):
            return Response(
                {'detail': 'Meeting kann nicht abgesagt werden.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        meeting.cancel()
        return Response(MeetingSerializer(meeting).data)

    @action(detail=True, methods=['get'], url_path='join_url')
    def join_url(self, request, pk=None):
        """Jitsi-JWT-Token und Join-URL für ein laufendes Meeting abrufen."""
        from jitsi.models import Meeting
        from jitsi.views import _build_token, JITSI_URL

        meeting = self.get_object()
        if meeting.status != Meeting.STATUS_RUNNING:
            return Response(
                {'detail': 'Meeting läuft gerade nicht.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        is_participant = (
            meeting.organizer == request.user
            or meeting.invitees.filter(pk=request.user.pk).exists()
            or request.user.is_superuser
        )
        if not is_participant:
            return Response(
                {'detail': 'Nicht eingeladen.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        token = _build_token(request.user, meeting.room_name)
        return Response({
            'token': token,
            'url': f"{JITSI_URL}/{meeting.room_name}?jwt={token}",
            'room_name': meeting.room_name,
        })
