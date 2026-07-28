import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# get_asgi_application() must be called before importing anything that
# touches Django models/apps (routing, consumers) — Django's app
# registry isn't populated yet otherwise.
django_asgi_app = get_asgi_application()

from apps.realtime.middleware import TicketAuthMiddleware  # noqa: E402
from apps.realtime.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": TicketAuthMiddleware(URLRouter(websocket_urlpatterns)),
})
