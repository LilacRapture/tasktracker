import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.cache import caches

User = get_user_model()
logger = logging.getLogger(__name__)

TICKET_CACHE_PREFIX = "ws_ticket:"


class TicketAuthMiddleware:
    """Websocket only: resolves the one-time `?ticket=` to `scope["user"]`, or None if invalid.

    The consumer closes the connection when `scope["user"]` is None.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] != "websocket":
            return await self.inner(scope, receive, send)

        query_string = scope.get("query_string", b"").decode()
        ticket = parse_qs(query_string).get("ticket", [None])[0]

        scope["user"] = await self._resolve_ticket(ticket) if ticket else None
        return await self.inner(scope, receive, send)

    @database_sync_to_async
    def _resolve_ticket(self, ticket: str):
        cache = caches["default"]
        key = f"{TICKET_CACHE_PREFIX}{ticket}"
        user_id = cache.get(key)
        if user_id is None:
            logger.info("WS ticket invalid or expired")
            return None

        # Not atomic with get(): a concurrent double-connect could slip through (accepted, ADR-014).
        cache.delete(key)

        try:
            return User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None
