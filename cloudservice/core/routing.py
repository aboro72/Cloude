"""
WebSocket routing for Django Channels.
Real-time updates for file operations and messenger chat.
"""

from django.urls import path
from core.consumers import NotificationConsumer, FileUploadConsumer
from messenger.consumers import ChatConsumer

websocket_urlpatterns = [
    path('ws/notifications/', NotificationConsumer.as_asgi(), name='ws_notifications'),
    path('ws/file-upload/', FileUploadConsumer.as_asgi(), name='ws_file_upload'),
    path('ws/messenger/<int:room_id>/', ChatConsumer.as_asgi(), name='ws_chat'),
]
