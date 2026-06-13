from django.urls import path

from .views import TaskDetailView, TaskListView

urlpatterns = [
    path("", TaskListView.as_view(), name="task-list"),
    path("<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
]
