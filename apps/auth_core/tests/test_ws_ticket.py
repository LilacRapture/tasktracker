import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.cache import cache

from apps.realtime.middleware import TICKET_CACHE_PREFIX, TicketAuthMiddleware
from apps.realtime.routing import websocket_urlpatterns

pytestmark = pytest.mark.django_db

WS_TICKET_URL = "/api/auth/ws-ticket/"


def test_authenticated_user_can_get_ticket(auth_client, developer_user):
    client = auth_client(developer_user)
    response = client.post(WS_TICKET_URL)

    assert response.status_code == 200
    assert "ticket" in response.json()


def test_ticket_requires_authentication(api_client):
    response = api_client.post(WS_TICKET_URL)
    assert response.status_code == 401


def test_ticket_is_stored_in_cache_with_correct_user(auth_client, developer_user):
    client = auth_client(developer_user)
    response = client.post(WS_TICKET_URL)

    ticket = response.json()["ticket"]
    cached_user_id = cache.get(f"{TICKET_CACHE_PREFIX}{ticket}")
    assert cached_user_id == developer_user.pk


def test_each_call_issues_a_different_ticket(auth_client, developer_user):
    client = auth_client(developer_user)
    ticket1 = client.post(WS_TICKET_URL).json()["ticket"]
    ticket2 = client.post(WS_TICKET_URL).json()["ticket"]

    assert ticket1 != ticket2

# ---------------------------------------------------------------------------
# e2e
# ---------------------------------------------------------------------------

def _build_ws_application():
    return TicketAuthMiddleware(URLRouter(websocket_urlpatterns))


@pytest.mark.django_db(transaction=True)
async def test_ticket_from_endpoint_is_accepted_by_ws_middleware(auth_client, developer_user):
    client = await database_sync_to_async(auth_client)(developer_user)
    response = await database_sync_to_async(client.post)("/api/auth/ws-ticket/")
    ticket = response.json()["ticket"]

    communicator = WebsocketCommunicator(_build_ws_application(), f"/ws/tasktracker/?ticket={ticket}")
    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.disconnect()
    await communicator.wait(timeout=1)
