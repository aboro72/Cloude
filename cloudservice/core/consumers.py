"""
WebSocket consumers for real-time updates.
Django Channels integration.
"""

import base64
import json
import logging
import mimetypes
import os
import shutil
from channels.generic.websocket import AsyncWebsocketConsumer, AsyncJsonWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.conf import settings
from django.db.models import Model as DjangoModel
from django.utils import timezone

from core.models import StorageFile, StorageFolder

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
        self.active_uploads = {}

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
            await self.handle_upload_start(content)
        elif message_type == 'upload_chunk':
            await self.handle_upload_chunk(content)

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

    async def handle_upload_start(self, content):
        upload_id = content.get('upload_id')
        file_name = content.get('file_name')
        folder_id = content.get('folder_id')

        try:
            total_size = int(content.get('total_size') or 0)
            total_chunks = int(content.get('total_chunks') or 0)
            if not upload_id or not file_name or total_size < 0 or total_chunks <= 0:
                raise ValueError('Ungueltige Upload-Parameter.')

            tmp_dir = await self.prepare_upload(upload_id, total_size)
            self.active_uploads[upload_id] = {
                'file_name': file_name,
                'total_size': total_size,
                'total_chunks': total_chunks,
                'folder_id': int(folder_id) if folder_id else None,
                'tmp_dir': tmp_dir,
            }

            await self.send_json({
                'type': 'upload_started',
                'upload_id': upload_id,
                'file_name': file_name,
                'file_size': total_size,
                'total_chunks': total_chunks,
            })
        except Exception as exc:
            logger.error("WebSocket upload start failed: %s", exc, exc_info=True)
            await self.send_json({
                'type': 'upload_error',
                'upload_id': upload_id,
                'error': str(exc),
            })

    async def handle_upload_chunk(self, content):
        upload_id = content.get('upload_id')
        upload = self.active_uploads.get(upload_id)

        if not upload:
            await self.send_json({
                'type': 'upload_error',
                'upload_id': upload_id,
                'error': 'Upload-Session nicht gefunden.',
            })
            return

        try:
            chunk_index = int(content.get('chunk_index'))
            encoded_data = content.get('data')
            if encoded_data is None:
                raise ValueError('Chunk-Daten fehlen.')

            is_complete = await self.store_chunk(
                upload['tmp_dir'],
                chunk_index,
                base64.b64decode(encoded_data),
                upload['total_chunks'],
            )

            if is_complete:
                storage_file = await self.finalize_upload(upload_id, upload)
                self.active_uploads.pop(upload_id, None)
                await self.send_json({
                    'type': 'upload_complete',
                    'upload_id': upload_id,
                    'file_id': storage_file['id'],
                    'file_name': storage_file['name'],
                    'file_size': storage_file['size'],
                })
                return

            await self.send_json({
                'type': 'chunk_received',
                'upload_id': upload_id,
                'chunk_index': chunk_index,
                'total_chunks': upload['total_chunks'],
                'progress': ((chunk_index + 1) / upload['total_chunks']) * 100,
            })
        except Exception as exc:
            logger.error("WebSocket upload chunk failed: %s", exc, exc_info=True)
            await self.cleanup_upload(upload)
            self.active_uploads.pop(upload_id, None)
            await self.send_json({
                'type': 'upload_error',
                'upload_id': upload_id,
                'error': str(exc),
            })

    @database_sync_to_async
    def prepare_upload(self, upload_id, total_size):
        remaining = self.user.profile.get_storage_remaining()
        if total_size > remaining:
            remaining_mb = remaining / (1024 * 1024)
            required_mb = total_size / (1024 * 1024)
            raise ValueError(
                f'Speicherlimit erreicht. Frei: {remaining_mb:.2f} MB, benoetigt: {required_mb:.2f} MB.'
            )

        tmp_dir = os.path.join(settings.MEDIA_ROOT, 'tmp_chunks', upload_id)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        os.makedirs(tmp_dir, exist_ok=True)
        return tmp_dir

    @database_sync_to_async
    def store_chunk(self, tmp_dir, chunk_index, chunk_bytes, total_chunks):
        chunk_path = os.path.join(tmp_dir, f'chunk_{chunk_index:06d}')
        with open(chunk_path, 'wb') as handle:
            handle.write(chunk_bytes)

        received = len([
            name for name in os.listdir(tmp_dir)
            if name.startswith('chunk_')
        ])
        return received >= total_chunks

    @database_sync_to_async
    def finalize_upload(self, upload_id, upload):
        folder = self.get_target_folder(upload.get('folder_id'))

        now = timezone.now()
        upload_subdir = now.strftime('files/%Y/%m/%d/%H%M%S')
        media_dir = os.path.join(settings.MEDIA_ROOT, upload_subdir)
        os.makedirs(media_dir, exist_ok=True)
        final_path = os.path.join(media_dir, upload['file_name'])

        with open(final_path, 'wb') as outfile:
            for index in range(upload['total_chunks']):
                part = os.path.join(upload['tmp_dir'], f'chunk_{index:06d}')
                with open(part, 'rb') as infile:
                    shutil.copyfileobj(infile, outfile, length=1024 * 1024)

        file_size = os.path.getsize(final_path)
        remaining = self.user.profile.get_storage_remaining()
        if file_size > remaining:
            raise ValueError('Speicherlimit erreicht.')

        mime_type, _ = mimetypes.guess_type(upload['file_name'])
        storage_file = StorageFile(
            owner=self.user,
            folder=folder,
            name=upload['file_name'],
            size=file_size,
            mime_type=mime_type or 'application/octet-stream',
            file_hash=f'ws-chunked-{upload_id[:32]}',
        )
        storage_file.file.name = f'{upload_subdir}/{upload["file_name"]}'
        DjangoModel.save(storage_file)

        shutil.rmtree(upload['tmp_dir'], ignore_errors=True)
        return {
            'id': storage_file.id,
            'name': storage_file.name,
            'size': storage_file.size,
        }

    @database_sync_to_async
    def cleanup_upload(self, upload):
        tmp_dir = upload.get('tmp_dir')
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def get_target_folder(self, folder_id):
        if folder_id:
            folder = StorageFolder.objects.filter(
                id=folder_id,
                owner=self.user,
            ).first()
            if folder:
                return folder

        root_folder = StorageFolder.objects.filter(owner=self.user, parent=None).first()
        if root_folder:
            return root_folder

        return StorageFolder.objects.create(
            owner=self.user,
            parent=None,
            name='Root',
            description='Root folder',
        )


from django.utils import timezone as now
