"""
WebSocket consumers for real-time updates.
Django Channels integration.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer, AsyncJsonWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    """

    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope['user']

        if self.user.is_authenticated:
            self.user_group_name = f'user_{self.user.id}_notifications'

            # Join user's notification group
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )

            await self.accept()
            logger.info(f"User {self.user.username} connected to notifications")
        else:
            await self.close()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.user.is_authenticated:
            # Leave notification group
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            logger.info(f"User {self.user.username} disconnected from notifications")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': str(now()),
                }))
        except json.JSONDecodeError:
            logger.error("Invalid JSON received from WebSocket")

    async def notification_message(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event['title'],
            'message': event['message'],
            'notification_type': event['notification_type'],
            'timestamp': event['timestamp'],
        }))

    async def file_event(self, event):
        """Send file event to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'file_event',
            'action': event['action'],
            'file_id': event['file_id'],
            'file_name': event['file_name'],
            'timestamp': event['timestamp'],
        }, cls=DjangoJSONEncoder))


class FileUploadConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for file upload progress tracking.
    """

    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope['user']

        if self.user.is_authenticated:
            self.upload_group = f'user_{self.user.id}_uploads'

            # Join upload group
            await self.channel_layer.group_add(
                self.upload_group,
                self.channel_name
            )

            await self.accept()
            logger.info(f"User {self.user.username} connected for file uploads")
        else:
            await self.close()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(
                self.upload_group,
                self.channel_name
            )

    async def receive_json(self, content):
        """Handle incoming JSON messages"""
        message_type = content.get('type')

        if message_type == 'upload_start':
            file_name = content.get('file_name')
            file_size = content.get('file_size')

            await self.send_json({
                'type': 'upload_started',
                'file_name': file_name,
                'file_size': file_size,
            })

        elif message_type == 'upload_complete':
            file_id = content.get('file_id')

            await self.channel_layer.group_send(
                self.upload_group,
                {
                    'type': 'upload_complete',
                    'file_id': file_id,
                    'file_name': content.get('file_name'),
                }
            )

    async def upload_progress(self, event):
        """Send upload progress to WebSocket"""
        await self.send_json({
            'type': 'upload_progress',
            'file_id': event['file_id'],
            'progress': event['progress'],
            'speed': event['speed'],
        })

    async def upload_complete(self, event):
        """Send upload completion to WebSocket"""
        await self.send_json({
            'type': 'upload_complete',
            'file_id': event['file_id'],
            'file_name': event['file_name'],
        })

    async def upload_error(self, event):
        """Send upload error to WebSocket"""
        await self.send_json({
            'type': 'upload_error',
            'file_id': event['file_id'],
            'error': event['error'],
        })


from django.utils import timezone as now
