"""
WebSocket consumer for real-time chat.
Each room has a dedicated channel group: messenger_room_<room_id>
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f'messenger_room_{self.room_id}'
        user = self.scope.get('user')

        if not user or not user.is_authenticated:
            await self.close()
            return

        if not await self.user_can_access(user, self.room_id):
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send typing indicator group name so client knows it
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'room_id': int(self.room_id),
        }))

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type')
        user = self.scope['user']

        if msg_type == 'chat_message':
            content = (data.get('content') or '').strip()
            if not content:
                return
            message = await self.save_message(user, self.room_id, content, data.get('reply_to_id'))
            if message:
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'chat.message',
                    'message': message.to_ws_dict(),
                })

        elif msg_type == 'typing':
            author_name = user.get_full_name() or user.username
            await self.channel_layer.group_send(self.group_name, {
                'type': 'chat.typing',
                'user_id': user.pk,
                'author': author_name,
            })

        elif msg_type == 'mark_read':
            await self.mark_room_read(user, self.room_id)

        elif msg_type == 'delete_message':
            msg_id = data.get('message_id')
            if msg_id:
                deleted = await self.delete_message(user, msg_id)
                if deleted:
                    await self.channel_layer.group_send(self.group_name, {
                        'type': 'chat.deleted',
                        'message_id': msg_id,
                    })

        elif msg_type == 'react':
            msg_id = data.get('message_id')
            emoji = (data.get('emoji') or '').strip()
            if msg_id and emoji:
                reactions = await self.toggle_reaction(user, msg_id, emoji)
                if reactions is not None:
                    await self.channel_layer.group_send(self.group_name, {
                        'type': 'chat.reaction',
                        'message_id': msg_id,
                        'reactions': reactions,
                    })

    # ── Channel-layer event handlers ──────────────────────────────────────

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
        }))

    async def chat_typing(self, event):
        if event['user_id'] != self.scope['user'].pk:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'author': event['author'],
            }))

    async def chat_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
        }))

    async def chat_reaction(self, event):
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'message_id': event['message_id'],
            'reactions': event['reactions'],
        }))

    # ── DB helpers ────────────────────────────────────────────────────────

    @database_sync_to_async
    def user_can_access(self, user, room_id):
        from messenger.models import ChatMembership
        return ChatMembership.objects.filter(room_id=room_id, user=user).exists()

    @database_sync_to_async
    def save_message(self, user, room_id, content, reply_to_id=None):
        from messenger.models import ChatMessage, ChatRoom, ChatMembership
        from core.models import Notification
        try:
            room = ChatRoom.objects.get(pk=room_id)
            msg = ChatMessage.objects.create(
                room=room,
                author=user,
                content=content,
                reply_to_id=reply_to_id,
                message_type='text',
            )
            room.updated_at = timezone.now()
            room.save(update_fields=['updated_at'])

            # Benachrichtigung für alle Raum-Mitglieder außer dem Sender
            sender_name = user.get_full_name() or user.username
            room_name = room.name or 'Direktnachricht'
            preview = content[:80] + ('…' if len(content) > 80 else '')
            recipients = ChatMembership.objects.filter(room=room).exclude(user=user).select_related('user')
            for membership in recipients:
                # Nur eine Notification pro Raum (neueste überschreibt nicht, aber dupliziere nicht innerhalb von 60s)
                recent = Notification.objects.filter(
                    user=membership.user,
                    notification_type='message',
                    url__endswith=f'/messenger/channel/{room.slug}/',
                    is_read=False,
                    created_at__gte=timezone.now() - timezone.timedelta(seconds=60),
                ).exists()
                if not recent:
                    Notification.objects.create(
                        user=membership.user,
                        notification_type='message',
                        title=f'Neue Nachricht in {room_name}',
                        message=f'{sender_name}: {preview}',
                        url=f'/{room.company.workspace_key}/messenger/channel/{room.slug}/',
                    )
            return msg
        except Exception:
            return None

    @database_sync_to_async
    def mark_room_read(self, user, room_id):
        from messenger.models import ChatMembership, ChatRoom
        from core.models import Notification
        ChatMembership.objects.filter(room_id=room_id, user=user).update(
            last_read_at=timezone.now()
        )
        # Messenger-Benachrichtigungen für diesen Raum als gelesen markieren
        try:
            room = ChatRoom.objects.get(pk=room_id)
            Notification.objects.filter(
                user=user,
                notification_type='message',
                url__endswith=f'/messenger/channel/{room.slug}/',
                is_read=False,
            ).update(is_read=True)
        except Exception:
            pass

    @database_sync_to_async
    def delete_message(self, user, message_id):
        from messenger.models import ChatMessage
        try:
            msg = ChatMessage.objects.get(pk=message_id)
            if msg.author == user or user.is_superuser:
                msg.soft_delete()
                return True
        except ChatMessage.DoesNotExist:
            pass
        return False

    @database_sync_to_async
    def toggle_reaction(self, user, message_id, emoji):
        from messenger.models import ChatMessage
        try:
            msg = ChatMessage.objects.get(pk=message_id)
            reactions = msg.reactions or {}
            user_id_str = str(user.pk)
            users = reactions.get(emoji, [])
            if user_id_str in users:
                users.remove(user_id_str)
            else:
                users.append(user_id_str)
            if users:
                reactions[emoji] = users
            else:
                reactions.pop(emoji, None)
            msg.reactions = reactions
            msg.save(update_fields=['reactions'])
            return reactions
        except ChatMessage.DoesNotExist:
            return None
