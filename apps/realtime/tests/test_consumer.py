import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.realtime.middleware import TICKET_CACHE_PREFIX
from apps.realtime.routing import websocket_urlpatterns
from apps.realtime.middleware import TicketAuthMiddleware
from channels.routing import URLRouter

User = get_user_model()

pytestmark = pytest.mark.django_db(transaction=True)


def _build_application():
    return TicketAuthMiddleware(URLRouter(websocket_urlpatterns))


@pytest.fixture
def user():
    return User.objects.create_user(
        email="ws@example.com", password="testpass123",
        first_name="WS", last_name="User",
    )


@pytest.fixture
def valid_ticket(user):
    ticket = "test-ticket-123"
    cache.set(f"{TICKET_CACHE_PREFIX}{ticket}", user.pk, timeout=20)
    return ticket


async def test_connect_with_valid_ticket_is_accepted(valid_ticket):
    communicator = WebsocketCommunicator(_build_application(), f"/ws/tasktracker/?ticket={valid_ticket}")
    connected, _ = await communicator.connect()
    assert connected is True
    await communicator.disconnect()
    await communicator.wait(timeout=1)


async def test_connect_with_missing_ticket_is_rejected():
    communicator = WebsocketCommunicator(_build_application(), "/ws/tasktracker/")
    connected, _ = await communicator.connect()
    assert connected is False
    await communicator.wait(timeout=1)


async def test_connect_with_invalid_ticket_is_rejected():
    communicator = WebsocketCommunicator(_build_application(), "/ws/tasktracker/?ticket=garbage")
    connected, _ = await communicator.connect()
    assert connected is False
    await communicator.wait(timeout=1)


async def test_ticket_is_single_use(valid_ticket):
    communicator1 = WebsocketCommunicator(_build_application(), f"/ws/tasktracker/?ticket={valid_ticket}")
    connected1, _ = await communicator1.connect()
    assert connected1 is True
    await communicator1.disconnect()
    await communicator1.wait(timeout=1)

    communicator2 = WebsocketCommunicator(_build_application(), f"/ws/tasktracker/?ticket={valid_ticket}")
    connected2, _ = await communicator2.connect()
    assert connected2 is False
    await communicator2.wait(timeout=1)


async def test_echo_round_trip(valid_ticket):
    communicator = WebsocketCommunicator(_build_application(), f"/ws/tasktracker/?ticket={valid_ticket}")
    await communicator.connect()
    await communicator.send_json_to({"hello": "world"})
    response = await communicator.receive_json_from()
    assert response == {"v": 1, "type": "echo", "payload": {"hello": "world"}}
    await communicator.disconnect()
    await communicator.wait(timeout=1)
