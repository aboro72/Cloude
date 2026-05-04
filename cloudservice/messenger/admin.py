from django.contrib import admin
from messenger.models import ChatRoom, ChatMembership, ChatMessage, ChatInvite


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'room_type', 'is_private', 'is_archived', 'member_count', 'created_at')
    list_filter = ('room_type', 'is_private', 'is_archived', 'company')
    search_fields = ('name', 'slug', 'company__name')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Mitglieder')
    def member_count(self, obj):
        return obj.memberships.count()


@admin.register(ChatMembership)
class ChatMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'role', 'joined_at', 'is_muted')
    list_filter = ('role', 'is_muted')
    search_fields = ('user__username', 'room__name')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'author', 'message_type', 'short_content', 'is_deleted', 'created_at')
    list_filter = ('message_type', 'is_deleted', 'room__company')
    search_fields = ('content', 'author__username', 'room__name')
    readonly_fields = ('created_at',)

    @admin.display(description='Inhalt')
    def short_content(self, obj):
        return obj.content[:60] if obj.content else f'[{obj.get_message_type_display()}]'


@admin.register(ChatInvite)
class ChatInviteAdmin(admin.ModelAdmin):
    list_display = ('room', 'invited_by', 'invited_email', 'use_count', 'max_uses', 'expires_at', 'created_at')
    search_fields = ('room__name', 'invited_email', 'invited_by__username')
    readonly_fields = ('token', 'created_at')
