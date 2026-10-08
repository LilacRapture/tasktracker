import pytest
from django.test import override_settings


@pytest.fixture(autouse=True)
def _in_memory_channel_layer():
    """The real Redis layer binds to the first event loop, but pytest-asyncio makes one per test."""
    with override_settings(
        CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    ):
        yield
