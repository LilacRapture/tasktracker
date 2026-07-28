import json
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = 1


class TaskTrackerConsumer(AsyncJsonWebsocketConsumer):
    """
    Phase 1 skeleton: accepts only authenticated connections (ticket
    resolved by TicketAuthMiddleware), joins the user's personal group
    (user_{id}), and echoes back anything received — no real task/
    presence event handling yet (see ADR-014 for the full design;
    that logic lands in Phase 2/3/4).
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None:
            await self.close(code=4001)  # 4001: custom code, invalid/missing ticket
            return

        self.user = user
        self.group_name = f"user_{user.pk}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("WS connected: user=%s group=%s", user.email, self.group_name)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Phase 1 placeholder — echoes back what it received, wrapped
        # in the envelope format, just to prove the round-trip works.
        await self.send_json({"v": PROTOCOL_VERSION, "type": "echo", "payload": content})

    async def broadcast_event(self, event):
        """
        Handler for messages sent via channel_layer.group_send() with
        {"type": "broadcast_event", "envelope": {...}} — Phase 3 will
        call this from TaskWriteSerializer. Kept here now, unused, so
        the consumer's group-message contract is visible from Phase 1.
        """
        await self.send_json(event["envelope"])
