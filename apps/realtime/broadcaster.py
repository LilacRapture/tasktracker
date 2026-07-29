import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

from apps.tasks.models import Task

User = get_user_model()
logger = logging.getLogger(__name__)

PROTOCOL_VERSION = 1


def _users_with_task_access(task: Task) -> list:
    """
    All active users who can currently read this task.

    Mirrors check_access()'s precedence for the "read" action on the
    "task" resource (see docs/rbac-schema.md): can_read_all grants
    access regardless of ownership; can_read only grants access to the
    task's own owner. Computed as two set-based queries rather than
    iterating every active user and calling check_access() per user —
    that approach was O(2N+1) queries (N = active user count); this is
    O(1) regardless of user count.

    Deliberately duplicates the precedence rule rather than reusing
    check_access() directly — the tradeoff is a second place to keep in
    sync with docs/rbac-schema.md if the RBAC schema ever grows a third
    access tier, in exchange for avoiding per-user query overhead on
    every task write.
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
    """
    Sends a task.{created,updated,deleted} envelope to every user
    currently allowed to read this task, via their personal
    user_{id} channel group (see ADR-014).
    """
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
