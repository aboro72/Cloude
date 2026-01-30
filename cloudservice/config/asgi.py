"""
ASGI config for CloudService project.
Supports WebSockets via Channels and Daphne
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.layers import get_channel_layer
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Import WebSocket URLs after Django setup
from core.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # HTTP & WebSocket
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
