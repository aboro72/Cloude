"""
Django REST Framework Serializers for CloudService API.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from core.models import StorageFile, StorageFolder, FileVersion, ActivityLog, Notification
from accounts.models import UserProfile
from sharing.models import UserShare, PublicLink, SharePermission
from storage.models import StorageStats
import logging

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']
        read_only_fields = ['id']

    def get_profile(self, obj):
        """Get user profile data"""
        if hasattr(obj, 'profile'):
            return UserProfileSerializer(obj.profile).data
        return None


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model"""
    storage_used = serializers.SerializerMethodField()
    storage_remaining = serializers.SerializerMethodField()
    storage_used_percentage = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'id', 'role', 'phone_number', 'bio', 'website',
            'language', 'timezone', 'theme', 'storage_quota',
            'storage_used', 'storage_remaining', 'storage_used_percentage',
            'is_email_verified', 'is_two_factor_enabled', 'is_active'
        ]
        read_only_fields = ['id', 'storage_used', 'storage_remaining', 'storage_used_percentage']

    def get_storage_used(self, obj):
        """Get storage used in MB"""
        return obj.get_storage_used_mb()

    def get_storage_remaining(self, obj):
        """Get storage remaining in MB"""
        return obj.get_storage_remaining_mb()

    def get_storage_used_percentage(self, obj):
        """Get storage used percentage"""
        return obj.get_storage_used_percentage()


class StorageFolderSerializer(serializers.ModelSerializer):
    """Serializer for StorageFolder model"""
    breadcrumb = serializers.SerializerMethodField()
    file_count = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()

    class Meta:
        model = StorageFolder
        fields = [
            'id', 'name', 'parent', 'owner', 'description',
            'is_public', 'is_starred', 'created_at', 'updated_at',
            'breadcrumb', 'file_count', 'size'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_breadcrumb(self, obj):
        """Get breadcrumb path"""
        return [{'id': f.id, 'name': f.name} for f in obj.breadcrumb]

    def get_file_count(self, obj):
        """Get total file count"""
        return obj.get_file_count()

    def get_size(self, obj):
        """Get folder size in MB"""
        return obj.get_size() / (1024 * 1024)


class FileVersionSerializer(serializers.ModelSerializer):
    """Serializer for FileVersion model"""
    class Meta:
        model = FileVersion
        fields = [
            'id', 'version_number', 'size', 'file_hash',
            'change_description', 'is_current', 'created_at'
        ]
        read_only_fields = fields


class StorageFileSerializer(serializers.ModelSerializer):
    """Serializer for StorageFile model"""
    icon_class = serializers.SerializerMethodField()
    extension = serializers.SerializerMethodField()
    size_mb = serializers.SerializerMethodField()

    class Meta:
        model = StorageFile
        fields = [
            'id', 'name', 'owner', 'folder', 'file', 'size', 'size_mb',
            'mime_type', 'description', 'is_public', 'is_starred',
            'version_count', 'download_count', 'last_accessed',
            'icon_class', 'extension', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'owner', 'file_hash', 'created_at', 'updated_at',
            'version_count', 'download_count', 'last_accessed'
        ]

    def get_icon_class(self, obj):
        """Get icon class for file type"""
        return obj.get_icon_class()

    def get_extension(self, obj):
        """Get file extension"""
        return obj.get_extension()

    def get_size_mb(self, obj):
        """Get file size in MB"""
        return obj.size / (1024 * 1024)


class StorageFileDetailSerializer(StorageFileSerializer):
    """Detailed serializer for StorageFile with versions"""
    versions = FileVersionSerializer(many=True, read_only=True)

    class Meta(StorageFileSerializer.Meta):
        fields = StorageFileSerializer.Meta.fields + ['versions']


class SharePermissionSerializer(serializers.ModelSerializer):
    """Serializer for SharePermission model"""
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = SharePermission
        fields = [
            'id', 'user', 'user_username', 'permission_type',
            'granted_by', 'granted_at'
        ]
        read_only_fields = ['id', 'granted_by', 'granted_at']


class UserShareSerializer(serializers.ModelSerializer):
    """Serializer for UserShare model"""
    shared_by = serializers.CharField(source='owner.username', read_only=True)
    shared_with_username = serializers.CharField(source='shared_with.username', read_only=True)

    class Meta:
        model = UserShare
        fields = [
            'id', 'owner', 'shared_by', 'shared_with', 'shared_with_username',
            'permission', 'message', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']


class PublicLinkSerializer(serializers.ModelSerializer):
    """Serializer for PublicLink model"""
    url = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = PublicLink
        fields = [
            'id', 'token', 'permission', 'title', 'description',
            'expires_at', 'allow_download', 'is_active', 'url',
            'view_count', 'download_count', 'is_expired',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'token', 'created_at', 'updated_at',
            'view_count', 'download_count', 'is_expired'
        ]
        extra_kwargs = {
            'password_hash': {'write_only': True}
        }

    def get_url(self, obj):
        """Get public link URL"""
        return obj.get_url()

    def get_is_expired(self, obj):
        """Check if link is expired"""
        return obj.is_expired()


class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for ActivityLog model"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'user', 'user_username', 'activity_type', 'activity_type_display',
            'file', 'folder', 'description', 'ip_address', 'created_at'
        ]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'notification_type_display',
            'title', 'message', 'is_read', 'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'created_at']


class StorageStatsSerializer(serializers.ModelSerializer):
    """Serializer for StorageStats model"""
    total_size_mb = serializers.SerializerMethodField()
    total_size_gb = serializers.SerializerMethodField()

    class Meta:
        model = StorageStats
        fields = [
            'user', 'total_files', 'total_folders', 'total_size',
            'total_size_mb', 'total_size_gb', 'total_versions', 'last_updated'
        ]
        read_only_fields = fields

    def get_total_size_mb(self, obj):
        """Get total size in MB"""
        return obj.get_total_size_mb()

    def get_total_size_gb(self, obj):
        """Get total size in GB"""
        return obj.get_total_size_gb()


class FileUploadSerializer(serializers.ModelSerializer):
    """Serializer for file uploads"""
    class Meta:
        model = StorageFile
        fields = ['id', 'file', 'folder', 'name', 'description']

    def create(self, validated_data):
        """Create file and set owner"""
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class BulkDeleteSerializer(serializers.Serializer):
    """Serializer for bulk delete operations"""
    file_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    folder_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )

    def validate(self, data):
        """At least one ID must be provided"""
        if not data.get('file_ids') and not data.get('folder_ids'):
            raise serializers.ValidationError("At least one file or folder ID must be provided")
        return data


class SearchResultSerializer(serializers.Serializer):
    """Serializer for search results"""
    type = serializers.CharField()
    id = serializers.IntegerField()
    name = serializers.CharField()
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        """Get URL for result"""
        if obj['type'] == 'file':
            return f"/storage/file/{obj['id']}/"
        elif obj['type'] == 'folder':
            return f"/storage/folder/{obj['id']}/"
        return None


# ── Departments ───────────────────────────────────────────────────────────────

class DepartmentMemberSerializer(serializers.Serializer):
    """Flattened membership entry (user + role)"""
    user_id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username')
    full_name = serializers.SerializerMethodField()
    role = serializers.CharField()
    joined_at = serializers.DateTimeField()

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class DepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.SerializerMethodField()
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        from departments.models import Department
        model = Department
        fields = ['id', 'name', 'slug', 'description', 'icon', 'color',
                  'head', 'head_name', 'member_count', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

    def get_head_name(self, obj):
        if obj.head:
            return obj.head.get_full_name() or obj.head.username
        return None


# ── Team Sites (GroupShare) ───────────────────────────────────────────────────

class GroupShareSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        from sharing.models import GroupShare
        model = GroupShare
        fields = ['id', 'group_name', 'owner', 'owner_name', 'permission',
                  'member_count', 'content_type', 'object_id']
        read_only_fields = ['id', 'owner']

    def get_member_count(self, obj):
        return obj.members.count()


# ── Kanban / Tasks ────────────────────────────────────────────────────────────

class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        from tasks_board.models import Task
        model = Task
        fields = ['id', 'board', 'title', 'description', 'status', 'priority',
                  'assigned_to', 'assigned_to_name', 'due_date', 'order',
                  'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.username
        return None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class TaskBoardSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    task_count = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    team_site_name = serializers.CharField(source='team_site.group_name', read_only=True)

    class Meta:
        from tasks_board.models import TaskBoard
        model = TaskBoard
        fields = ['id', 'title', 'color', 'owner', 'owner_name',
                  'department', 'department_name', 'team_site', 'team_site_name',
                  'task_count', 'created_at']
        read_only_fields = ['id', 'owner', 'created_at']

    def get_task_count(self, obj):
        return obj.tasks.count()


# ── News ──────────────────────────────────────────────────────────────────────

class NewsCategorySerializer(serializers.ModelSerializer):
    class Meta:
        from news.models import NewsCategory
        model = NewsCategory
        fields = ['id', 'name', 'slug', 'color', 'icon', 'order']
        read_only_fields = ['id', 'slug']


class NewsArticleSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        from news.models import NewsArticle
        model = NewsArticle
        fields = ['id', 'title', 'slug', 'category', 'category_name', 'tags',
                  'summary', 'author', 'author_name', 'is_published',
                  'is_featured', 'is_pinned', 'publish_at', 'view_count',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'slug', 'view_count', 'created_at', 'updated_at']

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.username
        return None


# ── Messenger ─────────────────────────────────────────────────────────────────

class ChatMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        from messenger.models import ChatMembership
        model = ChatMembership
        fields = ['id', 'user_id', 'username', 'full_name', 'role',
                  'joined_at', 'last_read_at', 'is_muted']
        read_only_fields = ['id', 'user_id', 'username', 'full_name', 'joined_at']

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class ChatMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    reply_to_preview = serializers.SerializerMethodField()
    storage_file_name = serializers.CharField(source='storage_file.name', read_only=True)

    class Meta:
        from messenger.models import ChatMessage
        model = ChatMessage
        fields = ['id', 'room', 'author_id', 'author_name', 'message_type',
                  'content', 'reply_to', 'reply_to_preview',
                  'storage_file', 'storage_file_name',
                  'reactions', 'is_edited', 'edited_at', 'is_deleted', 'created_at']
        read_only_fields = ['id', 'author_id', 'author_name', 'reply_to_preview',
                            'storage_file_name', 'is_edited', 'edited_at',
                            'is_deleted', 'created_at']

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.username
        return 'Gelöscht'

    def get_reply_to_preview(self, obj):
        if not obj.reply_to:
            return None
        return {
            'id': obj.reply_to.id,
            'author': obj.reply_to.author.username if obj.reply_to.author else 'Gelöscht',
            'content': obj.reply_to.content[:80] if not obj.reply_to.is_deleted else '[gelöscht]',
        }


class ChatRoomSerializer(serializers.ModelSerializer):
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        from messenger.models import ChatRoom
        model = ChatRoom
        fields = ['id', 'name', 'slug', 'room_type', 'description',
                  'is_private', 'is_archived', 'member_count',
                  'unread_count', 'last_message', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.unread_count(request.user)
        return 0

    def get_last_message(self, obj):
        msg = obj.get_last_message()
        if not msg:
            return None
        return {
            'id': msg.id,
            'author': msg.author.username if msg.author else 'Gelöscht',
            'content': msg.content[:60] if not msg.is_deleted else '[gelöscht]',
            'created_at': msg.created_at.isoformat(),
        }

    def get_member_count(self, obj):
        return obj.members.count()


class ChatRoomDetailSerializer(ChatRoomSerializer):
    memberships = ChatMembershipSerializer(many=True, read_only=True)

    class Meta(ChatRoomSerializer.Meta):
        fields = ChatRoomSerializer.Meta.fields + ['memberships', 'video_enabled',
                                                    'video_provider', 'updated_at']


class ChatInviteSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.name', read_only=True)
    invited_by_name = serializers.CharField(source='invited_by.username', read_only=True)
    is_valid = serializers.SerializerMethodField()

    class Meta:
        from messenger.models import ChatInvite
        model = ChatInvite
        fields = ['id', 'token', 'room', 'room_name', 'invited_by', 'invited_by_name',
                  'invited_email', 'max_uses', 'use_count', 'expires_at',
                  'created_at', 'is_valid']
        read_only_fields = ['id', 'token', 'invited_by', 'use_count', 'created_at']

    def get_is_valid(self, obj):
        return obj.is_valid()
