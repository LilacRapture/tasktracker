import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.rbac.permissions import check_access
from apps.realtime.broadcaster import broadcast_presence_editing_event
from apps.realtime.protocol import PROTOCOL_VERSION

logger = logging.getLogger(__name__)

# Joined/left go to every connected user, unscoped: bare presence isn't task content.
# Editing events reveal a task, so they're RBAC-scoped (see broadcaster.py).
PRESENCE_GROUP = "presence_board"

# Client -> server message types handled in receive_json.
EDITING_STARTED = "presence.editing_started"
EDITING_STOPPED = "presence.editing_stopped"


class TaskTrackerConsumer(AsyncJsonWebsocketConsumer):
    """Single WS endpoint for task events and presence; see docs/realtime.md."""

    async def connect(self):
        user = self.scope.get("user")
        if user is None:
            await self.close(code=4001)
            return

        self.user = user
        self.group_name = f"user_{user.pk}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.channel_layer.group_add(PRESENCE_GROUP, self.channel_name)
        await self.accept()

        await self.channel_layer.group_send(
            PRESENCE_GROUP,
            {
                "type": "broadcast_event",
                "sender_channel": self.channel_name,  # lets broadcast_event skip echoing back to the sender
                "envelope": {
                    "v": PROTOCOL_VERSION,
                    "type": "presence.joined",
                    "payload": {"user_id": user.pk, "email": user.email},
                },
            },
        )
        logger.info("WS connected: user=%s group=%s", user.email, self.group_name)

    async def disconnect(self, close_code):
        if not hasattr(self, "group_name"):
            return

        await self.channel_layer.group_send(
            PRESENCE_GROUP,
            {
                "type": "broadcast_event",
                "sender_channel": self.channel_name,
                "envelope": {
                    "v": PROTOCOL_VERSION,
                    "type": "presence.left",
                    "payload": {"user_id": self.user.pk, "email": self.user.email},
                },
            },
        )
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.channel_layer.group_discard(PRESENCE_GROUP, self.channel_name)

    async def receive_json(self, content, **kwargs):
        message_type = content.get("type")

        if message_type in (EDITING_STARTED, EDITING_STOPPED):
            await self._handle_editing_event(message_type, content)
            return

        # Placeholder for connectivity checks; remove once the frontend stops relying on it.
        await self.send_json({"v": PROTOCOL_VERSION, "type": "echo", "payload": content})

    async def _handle_editing_event(self, message_type: str, content: dict) -> None:
        task_id = content.get("payload", {}).get("task_id")
        if task_id is None:
            logger.warning("Editing event missing task_id, ignoring: %s", content)
            return

        task = await self._get_task_if_readable(task_id)
        if task is None:
            # Missing or unreadable: drop silently, the client may race a delete or permission change.
            logger.info(
                "Ignoring %s for task=%s: not found or not readable by user=%s",
                message_type, task_id, self.user.email,
            )
            return

        event_type = "presence.editing_started" if message_type == EDITING_STARTED else "presence.editing_stopped"
        await database_sync_to_async(broadcast_presence_editing_event)(task, self.user, event_type)

    @database_sync_to_async
    def _get_task_if_readable(self, task_id: int):
        from apps.tasks.models import Task

        try:
            task = Task.objects.select_related("owner").get(pk=task_id)
        except Task.DoesNotExist:
            return None

        if not check_access(self.user, "task", "read", obj_owner_id=task.owner_id):
            return None
        return task

    async def broadcast_event(self, event):
        """Deliver a group_send envelope, skipping the originating connection (`sender_channel`)."""
        if event.get("sender_channel") == self.channel_name:
            return
        await self.send_json(event["envelope"])
