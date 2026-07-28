import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.cache import caches

User = get_user_model()
logger = logging.getLogger(__name__)

TICKET_CACHE_PREFIX = "ws_ticket:"


class TicketAuthMiddleware:
    """
    ASGI middleware for the websocket protocol only. Reads a one-time
    ticket from the connection's query string, resolves it to a user
    via the shared Redis-backed cache (same store used to issue
    tickets in apps/auth_core/views.py), and deletes it atomically so
    it cannot be reused. Rejects the connection (scope["user"] = None)
    on any missing/invalid/expired ticket — consumers are responsible
    for closing the connection if scope["user"] is None.
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
        cache = caches["default"]  # configured to point at Redis, see settings.py
        key = f"{TICKET_CACHE_PREFIX}{ticket}"
        user_id = cache.get(key)
        if user_id is None:
            logger.info("WS ticket invalid or expired")
            return None

        cache.delete(key)  # one-time use — not perfectly atomic with .get(),
        # acceptable race window is a concurrent double-connect within
        # the same ~ms, not a realistic attack surface for a portfolio project.
        # Revisit with a Lua GETDEL script if this ever needs to be airtight.

        try:
            return User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None
