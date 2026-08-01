"""
Tests for presence behavior in TaskTrackerConsumer:
- user_joined/user_left broadcast to all connected users (unscoped —
  presence itself isn't RBAC content)
- editing_started/editing_stopped are RBAC-scoped like task events,
  reusing _users_with_task_access
"""
import uuid

import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.cache import cache

from apps.realtime.middleware import TICKET_CACHE_PREFIX, TicketAuthMiddleware
from apps.realtime.routing import websocket_urlpatterns
from apps.tasks.models import Task

pytestmark = pytest.mark.django_db(transaction=True)


def _build_application():
    return TicketAuthMiddleware(URLRouter(websocket_urlpatterns))


async def _connect_as(user):
    ticket = f"presence-test-{uuid.uuid4().hex}"  # unique per call, avoids collisions across tests
    await database_sync_to_async(cache.set)(f"{TICKET_CACHE_PREFIX}{ticket}", user.pk, timeout=20)
    communicator = WebsocketCommunicator(_build_application(), f"/ws/tasktracker/?ticket={ticket}")
    connected, _ = await communicator.connect()
    assert connected is True
    return communicator


async def _disconnect(communicator):
    await communicator.disconnect()
    await communicator.wait(timeout=1)


# ---------------------------------------------------------------------------
# user_joined / user_left — unscoped, visible to every connected user
# ---------------------------------------------------------------------------

async def test_second_connection_sees_presence_joined_for_first(developer_user, admin_user):
    first = await _connect_as(developer_user)
    second = await _connect_as(admin_user)

    event = await first.receive_json_from(timeout=1)
    assert event["type"] == "presence.joined"
    assert event["payload"]["user_id"] == admin_user.pk

    await _disconnect(first)
    await _disconnect(second)


async def test_disconnect_broadcasts_presence_left(developer_user, admin_user):
    first = await _connect_as(developer_user)
    second = await _connect_as(admin_user)

    # drain the presence.joined event second's connection triggered for first
    await first.receive_json_from(timeout=1)

    await _disconnect(second)

    event = await first.receive_json_from(timeout=1)
    assert event["type"] == "presence.left"
    assert event["payload"]["user_id"] == admin_user.pk

    await _disconnect(first)


async def test_presence_joined_is_not_rbac_scoped(developer_user, stranger_user):
    """
    stranger_user has zero task access, but must still see presence
    events — presence is not task content (see ADR-016).
    """
    first = await _connect_as(stranger_user)
    second = await _connect_as(developer_user)

    event = await first.receive_json_from(timeout=1)
    assert event["type"] == "presence.joined"
    assert event["payload"]["user_id"] == developer_user.pk

    await _disconnect(first)
    await _disconnect(second)


# ---------------------------------------------------------------------------
# editing_started / editing_stopped — RBAC-scoped like task events
# ---------------------------------------------------------------------------

async def test_editing_started_reaches_user_with_read_all_access(developer_user, admin_user):
    """admin has can_read_all on task — must receive the editing event."""
    task = await database_sync_to_async(Task.objects.create)(title="Shared task", owner=developer_user)

    editor = await _connect_as(developer_user)
    observer = await _connect_as(admin_user)

    # drain observer's own presence.joined-from-editor event ordering
    # isn't guaranteed relative to connect, so drain any presence event
    # first before asserting on the editing event specifically.
    await editor.send_json_to({
        "type": "presence.editing_started",
        "payload": {"task_id": task.id},
    })

    event = await observer.receive_json_from(timeout=1)

    assert event["type"] == "presence.editing_started"
    assert event["payload"]["task_id"] == task.id
    assert event["payload"]["user_id"] == developer_user.pk

    await _disconnect(editor)
    await _disconnect(observer)


async def test_editing_started_is_dropped_for_user_without_task_access(developer_user, stranger_user):
    """stranger has zero roles — must not receive the editing event."""
    task = await database_sync_to_async(Task.objects.create)(title="Private-ish task", owner=developer_user)

    editor = await _connect_as(developer_user)
    observer = await _connect_as(stranger_user)

    await editor.send_json_to({
        "type": "presence.editing_started",
        "payload": {"task_id": task.id},
    })

    assert await observer.receive_nothing(timeout=0.5) is True

    await _disconnect(editor)
    await _disconnect(observer)


async def test_editing_started_for_nonexistent_task_is_ignored(developer_user):
    editor = await _connect_as(developer_user)

    await editor.send_json_to({
        "type": "presence.editing_started",
        "payload": {"task_id": 999999},
    })

    # No crash, no event — nothing to assert on the sender itself beyond
    # "connection stays alive", proven by being able to disconnect cleanly.
    assert await editor.receive_nothing(timeout=0.5) is True

    await _disconnect(editor)


async def test_editing_started_missing_task_id_is_ignored(developer_user):
    editor = await _connect_as(developer_user)

    await editor.send_json_to({"type": "presence.editing_started", "payload": {}})

    assert await editor.receive_nothing(timeout=0.5) is True

    await _disconnect(editor)


async def test_editing_stopped_uses_same_rbac_scoping_as_editing_started(developer_user, admin_user):
    task = await database_sync_to_async(Task.objects.create)(title="Shared task", owner=developer_user)

    editor = await _connect_as(developer_user)
    observer = await _connect_as(admin_user)

    await editor.send_json_to({
        "type": "presence.editing_stopped",
        "payload": {"task_id": task.id},
    })

    event = await observer.receive_json_from(timeout=1)

    assert event["type"] == "presence.editing_stopped"
    assert event["payload"]["task_id"] == task.id

    await _disconnect(editor)
    await _disconnect(observer)
