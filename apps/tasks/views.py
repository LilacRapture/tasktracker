import logging

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rbac.permissions import RBACPermission, get_accessible_queryset

from .models import Task
from .serializers import TaskSerializer, TaskWriteSerializer

logger = logging.getLogger(__name__)


class TaskListView(generics.ListCreateAPIView):
    """
    GET  /api/tasks/  — list tasks accessible to the user (paginated)
    POST /api/tasks/  — create a new task (owner = caller)
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "task"
    rbac_action = "auto"

    def get_queryset(self):
        return get_accessible_queryset(
            self.request.user,
            "task",
            "read",
            Task.objects.select_related("owner", "project"),
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TaskWriteSerializer
        return TaskSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = TaskWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    """
    GET    /api/tasks/{id}/  — task detail
    PATCH  /api/tasks/{id}/  — update task
    DELETE /api/tasks/{id}/  — delete task
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "task"
    rbac_action = "auto"

    def get_rbac_owner_id(self, request: Request, obj: Task) -> int:
        return obj.owner_id

    def _get_object(self, request: Request, pk: int) -> Task | None:
        try:
            obj = Task.objects.select_related("owner", "project").get(pk=pk)
        except Task.DoesNotExist:
            return None
        self.check_object_permissions(request, obj)
        return obj

    def get(self, request: Request, pk: int) -> Response:
        obj = self._get_object(request, pk)
        if obj is None:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(TaskSerializer(obj).data)

    def patch(self, request: Request, pk: int) -> Response:
        obj = self._get_object(request, pk)
        if obj is None:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = TaskWriteSerializer(
            obj, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TaskSerializer(obj).data)

    def delete(self, request: Request, pk: int) -> Response:
        obj = self._get_object(request, pk)
        if obj is None:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        