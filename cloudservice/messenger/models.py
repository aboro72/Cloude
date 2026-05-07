"""
Messenger models for CloudService.
Company-scoped channels + direct messages + cross-company invitations.
Video conferencing fields prepared for future use.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify


class ChatRoom(models.Model):
    """A chat channel, group chat, or direct-message thread."""

    ROOM_TYPE_CHOICES = [
        ('channel', _('Channel')),
        ('direct', _('Direct Message')),
        ('group', _('Group Chat')),
    ]

    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='chat_rooms',
        verbose_name=_('Company'),
    )
    room_type = models.CharField(
        max_length=20,
        choices=ROOM_TYPE_CHOICES,
        default='channel',
        verbose_name=_('Room type'),
        db_index=True,
    )
    name = models.CharField(
        max_length=150,
        verbose_name=_('Name'),
    )
    slug = models.SlugField(
        max_length=150,
        verbose_name=_('Slug'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
    )
    is_private = models.BooleanField(
        default=False,
        verbose_name=_('Private'),
        help_text=_('Private channels require an invitation to join.'),
    )
    is_archived = models.BooleanField(
        default=False,
        verbose_name=_('Archived'),
        db_index=True,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_rooms',
        verbose_name=_('Created by'),
    )
    members = models.ManyToManyField(
        User,
        through='ChatMembership',
        related_name='chat_rooms',
        verbose_name=_('Members'),
    )
    # Cross-company: other companies allowed to join
    guest_companies = models.ManyToManyField(
        'accounts.Company',
        blank=True,
        related_name='guest_rooms',
        verbose_name=_('Guest companies'),
    )

    # ── Video conferencing (prepared, not yet active) ──────────────────────
    video_enabled = models.BooleanField(
        default=False,
        verbose_name=_('Video conferencing enabled'),
    )
    video_provider = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Video provider'),
        help_text=_('e.g. jitsi, daily, whereby — reserved for future use.'),
    )
    video_room_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Video room ID'),
    )
    # ──────────────────────────────────────────────────────────────────────

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    class Meta:
        unique_together = [['company', 'slug']]
        ordering = ['name']
        verbose_name = _('Chat Room')
        verbose_name_plural = _('Chat Rooms')

    def __str__(self):
        return f'{self.company.workspace_key} / {self.name}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_last_message(self):
        return self.messages.filter(is_deleted=False).order_by('-created_at').first()

    def unread_count(self, user):
        membership = self.memberships.filter(user=user).first()
        if not membership:
            return 0
        return self.messages.filter(
            created_at__gt=membership.last_read_at,
            is_deleted=False,
        ).exclude(author=user).count()


class ChatMembership(models.Model):
    """Membership of a user in a chat room."""

    ROLE_CHOICES = [
        ('owner', _('Owner')),
        ('admin', _('Admin')),
        ('member', _('Member')),
    ]

    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name=_('Room'),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='messenger_memberships',
        verbose_name=_('User'),
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='member',
        verbose_name=_('Role'),
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Joined at'))
    last_read_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Last read at'),
    )
    is_muted = models.BooleanField(default=False, verbose_name=_('Muted'))

    class Meta:
        unique_together = [['room', 'user']]
        verbose_name = _('Chat Membership')
        verbose_name_plural = _('Chat Memberships')

    def __str__(self):
        return f'{self.user.username} in {self.room.name}'

    def mark_read(self):
        self.last_read_at = timezone.now()
        self.save(update_fields=['last_read_at'])


class ChatMessage(models.Model):
    """A single message in a chat room."""

    MESSAGE_TYPE_CHOICES = [
        ('text', _('Text')),
        ('file', _('File')),
        ('system', _('System')),
        ('call_invite', _('Call Invite')),  # reserved for video
    ]

    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Room'),
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chat_messages',
        verbose_name=_('Author'),
    )
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='text',
        verbose_name=_('Type'),
        db_index=True,
    )
    content = models.TextField(blank=True, verbose_name=_('Content'))
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name=_('Reply to'),
    )
    # Attached file from storage
    storage_file = models.ForeignKey(
        'core.StorageFile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_attachments',
        verbose_name=_('Attached file'),
    )
    reactions = models.JSONField(
        default=dict,
        verbose_name=_('Reactions'),
        help_text=_('{"👍": ["user_id", ...], ...}'),
    )
    is_edited = models.BooleanField(default=False, verbose_name=_('Edited'))
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Edited at'))
    is_deleted = models.BooleanField(default=False, verbose_name=_('Deleted'), db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('Sent at'))

    class Meta:
        ordering = ['created_at']
        verbose_name = _('Chat Message')
        verbose_name_plural = _('Chat Messages')
        indexes = [
            models.Index(fields=['room', 'created_at']),
            models.Index(fields=['room', 'is_deleted']),
        ]

    def __str__(self):
        preview = self.content[:40] if self.content else f'[{self.get_message_type_display()}]'
        return f'{self.author}: {preview}'

    def soft_delete(self):
        self.is_deleted = True
        self.content = ''
        self.save(update_fields=['is_deleted', 'content'])

    def to_ws_dict(self):
        """Minimal dict for WebSocket broadcast."""
        author_name = (
            self.author.get_full_name() or self.author.username
            if self.author else 'Gelöscht'
        )
        return {
            'id': self.pk,
            'room_id': self.room_id,
            'author': author_name,
            'author_id': self.author_id,
            'content': self.content,
            'message_type': self.message_type,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.isoformat(),
            'reply_to_id': self.reply_to_id,
        }


class ChatInvite(models.Model):
    """Invitation token to join a room — usable cross-company."""

    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='invites',
        verbose_name=_('Room'),
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_chat_invites',
        verbose_name=_('Invited by'),
    )
    invited_email = models.EmailField(
        blank=True,
        verbose_name=_('Invited email'),
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_('Token'),
        db_index=True,
    )
    max_uses = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_('Max uses'),
        help_text=_('0 = unlimited'),
    )
    use_count = models.PositiveSmallIntegerField(default=0, verbose_name=_('Use count'))
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expires at'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Chat Invite')
        verbose_name_plural = _('Chat Invites')

    def __str__(self):
        return f'Invite to {self.room.name} by {self.invited_by.username}'

    def is_valid(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.max_uses > 0 and self.use_count >= self.max_uses:
            return False
        return True
