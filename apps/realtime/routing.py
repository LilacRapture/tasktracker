from django.urls import re_path

from .consumers import TaskTrackerConsumer

websocket_urlpatterns = [
    re_path(r"^ws/tasktracker/$", TaskTrackerConsumer.as_asgi()),
]
