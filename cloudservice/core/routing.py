"""
WebSocket routing for Django Channels.
Real-time updates for file operations.
"""

from django.urls import path
from core.consumers import NotificationConsumer, FileUploadConsumer

websocket_urlpatterns = [
    path('ws/notifications/', NotificationConsumer.as_asgi(), name='ws_notifications'),
    path('ws/file-upload/', FileUploadConsumer.as_asgi(), name='ws_file_upload'),
]
