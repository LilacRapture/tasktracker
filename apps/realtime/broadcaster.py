import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

from apps.realtime.protocol import PROTOCOL_VERSION
from apps.tasks.models import Task

User = get_user_model()
logger = logging.getLogger(__name__)


def _users_with_task_access(task: Task) -> list:
    """Active users who can read the task: `can_read_all` holders, plus the owner with `can_read`.

    Deliberately duplicates `check_access()`'s read precedence to stay at two queries instead
    of one per user — keep in sync with it (ADR-015).
    """
    read_all_user_ids = set(
        User.objects.filter(
            is_active=True,
            user_roles__role__access_rules__resource="task",
            user_roles__role__access_rules__can_read_all=True,
        ).values_list("id", flat=True).distinct()
    )

    owner_has_own_read = User.objects.filter(
        pk=task.owner_id,
        is_active=True,
        user_roles__role__access_rules__resource="task",
        user_roles__role__access_rules__can_read=True,
    ).distinct().exists()

    recipient_ids = read_all_user_ids | ({task.owner_id} if owner_has_own_read else set())
    return list(User.objects.filter(pk__in=recipient_ids))


def broadcast_task_event(task: Task, event_type: str) -> None:
    """Send a task.{created,updated,deleted} envelope to every user who can read the task."""
    channel_layer = get_channel_layer()
    envelope = {
        "v": PROTOCOL_VERSION,
        "type": event_type,
        "payload": {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "owner_id": task.owner_id,
            "project_id": task.project_id,
        },
    }

    recipients = _users_with_task_access(task)
    for user in recipients:
        async_to_sync(channel_layer.group_send)(
            f"user_{user.pk}",
            {"type": "broadcast_event", "envelope": envelope},
        )

    logger.debug(
        "Broadcast %s for task=%s to %d recipient(s)",
        event_type, task.id, len(recipients),
    )


def broadcast_presence_editing_event(task: Task, editing_user, event_type: str) -> None:
    """Send presence.editing_* to the same recipients as task events: it reveals the task, so it's RBAC-scoped."""
    channel_layer = get_channel_layer()
    envelope = {
        "v": PROTOCOL_VERSION,
        "type": event_type,
        "payload": {
            "task_id": task.id,
            "user_id": editing_user.pk,
            "email": editing_user.email,
        },
    }

    recipients = _users_with_task_access(task)
    for user in recipients:
        async_to_sync(channel_layer.group_send)(
            f"user_{user.pk}",
            {"type": "broadcast_event", "envelope": envelope},
        )

    logger.debug(
        "Broadcast %s for task=%s (by user=%s) to %d recipient(s)",
        event_type, task.id, editing_user.email, len(recipients),
    )
