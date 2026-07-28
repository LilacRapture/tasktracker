import pytest
from django.test import override_settings


@pytest.fixture(autouse=True)
def _in_memory_channel_layer():
    """
    Real channels-redis caches its Redis connection against the event
    loop active when first used. pytest-asyncio creates a fresh event
    loop per test function, so reusing the real layer across tests
    raises "Two event loops are trying to receive()". InMemoryChannelLayer
    has no such state, and is Channels' own recommended layer for
    testing — see docs. A real-Redis integration test for cross-process
    broadcast lands separately in Phase 3.
    """
    with override_settings(
        CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    ):
        yield
