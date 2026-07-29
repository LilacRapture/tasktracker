"""
Tests for apps/realtime/broadcaster.py.

Split into two groups:
- _users_with_task_access: pure RBAC recipient computation, no channel
  layer involved at all.
- broadcast_task_event: full WS round-trip via InMemoryChannelLayer
  (see apps/realtime/tests/conftest.py's autouse fixture), proving the
  envelope actually reaches a subscribed user's personal group.
"""
import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.cache import cache

from apps.rbac.models import UserRole
from apps.realtime.broadcaster import _users_with_task_access, broadcast_task_event
from apps.realtime.middleware import TICKET_CACHE_PREFIX, TicketAuthMiddleware
from apps.realtime.routing import websocket_urlpatterns
from apps.tasks.models import Task

pytestmark = pytest.mark.django_db(transaction=True)


def _build_application():
    return TicketAuthMiddleware(URLRouter(websocket_urlpatterns))


# ---------------------------------------------------------------------------
# _users_with_task_access — recipient computation (pure RBAC logic)
# ---------------------------------------------------------------------------

def test_owner_with_own_read_sees_their_task(developer_user):
    """developer has can_read=True (own) on task."""
    task = Task.objects.create(title="Own task", owner=developer_user)
    recipients = _users_with_task_access(task)
    assert developer_user in recipients


def test_read_all_user_sees_others_task(admin_user, developer_user):
    """admin has can_read_all=True on task — sees developer's task too."""
    task = Task.objects.create(title="Developer's task", owner=developer_user)
    recipients = _users_with_task_access(task)
    assert admin_user in recipients


def test_viewer_sees_others_task_via_read_all(developer_user, viewer_user):
    """
    viewer has can_read_all=True on task per seed data — this makes
    that assumption explicit rather than silently relying on it.
    """
    task = Task.objects.create(title="Developer's task", owner=developer_user)
    recipients = _users_with_task_access(task)
    assert viewer_user in recipients


def test_stranger_without_any_task_access_is_excluded(developer_user, stranger_user):
    """A user with zero roles must never appear in recipients."""
    task = Task.objects.create(title="Developer's task", owner=developer_user)
    recipients = _users_with_task_access(task)
    assert stranger_user not in recipients


def test_inactive_user_is_excluded_even_with_matching_role(admin_user, developer_user):
    admin_user.is_active = False
    admin_user.save(update_fields=["is_active"])

    task = Task.objects.create(title="Developer's task", owner=developer_user)
    recipients = _users_with_task_access(task)
    assert admin_user not in recipients


def test_recipients_contain_no_duplicates_when_user_has_multiple_qualifying_roles(
    developer_user, roles,
):
    """
    Regression guard for the .distinct() calls in _users_with_task_access:
    a user with two roles that both grant can_read_all on 'task' must
    still appear exactly once in the result, not once per matching role.
    """

    UserRole.objects.create(user=developer_user, role=roles["admin"])  # 2nd role, also can_read_all

    task = Task.objects.create(title="Developer's task", owner=developer_user)
    recipients = _users_with_task_access(task)

    assert recipients.count(developer_user) == 1


# ---------------------------------------------------------------------------
# broadcast_task_event — full WS round-trip via InMemoryChannelLayer
# ---------------------------------------------------------------------------

async def test_broadcast_task_created_reaches_subscribed_user(developer_user):
    ticket = "broadcast-test-ticket"
    await database_sync_to_async(cache.set)(f"{TICKET_CACHE_PREFIX}{ticket}", developer_user.pk, timeout=20)

    communicator = WebsocketCommunicator(_build_application(), f"/ws/tasktracker/?ticket={ticket}")
    connected, _ = await communicator.connect()
    assert connected is True

    task = await database_sync_to_async(Task.objects.create)(title="Test task", owner=developer_user)
    await database_sync_to_async(broadcast_task_event)(task, "task.created")

    response = await communicator.receive_json_from(timeout=1)
    assert response == {
        "v": 1,
        "type": "task.created",
        "payload": {
            "id": task.id,
            "title": "Test task",
            "status": "todo",
            "owner_id": developer_user.id,
            "project_id": None,
        },
    }

    await communicator.disconnect()
    await communicator.wait(timeout=1)


async def test_broadcast_does_not_reach_user_without_task_access(developer_user, stranger_user):
    """
    stranger_user has no roles at all — must not receive the event even
    though they're connected and listening on their own group.
    """
    ticket = "broadcast-test-ticket-stranger"
    await database_sync_to_async(cache.set)(f"{TICKET_CACHE_PREFIX}{ticket}", stranger_user.pk, timeout=20)

    communicator = WebsocketCommunicator(_build_application(), f"/ws/tasktracker/?ticket={ticket}")
    connected, _ = await communicator.connect()
    assert connected is True

    task = await database_sync_to_async(Task.objects.create)(title="Test task", owner=developer_user)
    await database_sync_to_async(broadcast_task_event)(task, "task.created")

    # receive_nothing() is purpose-built for "assert nothing arrived" —
    # unlike wrapping receive_json_from() in pytest.raises(TimeoutError),
    # it doesn't risk cancelling the communicator's underlying
    # application task as a side effect, which was leaving self.future
    # in a cancelled state before the subsequent disconnect() call.
    assert await communicator.receive_nothing(timeout=0.5) is True

    await communicator.disconnect()
    await communicator.wait(timeout=1)
