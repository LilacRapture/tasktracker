import logging

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rbac.permissions import RBACPermission, get_accessible_queryset

from .filters import ProjectFilter
from .models import Project
from .serializers import ProjectSerializer

logger = logging.getLogger(__name__)


class ProjectListView(generics.ListCreateAPIView):
    """
    GET  /api/projects/  — list projects accessible to the user (paginated)
    POST /api/projects/  — create a new project (owner = caller)
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "project"
    rbac_action = "auto"
    serializer_class = ProjectSerializer
    
    filterset_class = ProjectFilter
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "updated_at", "name", "status"]

    def get_queryset(self):
        return get_accessible_queryset(
            self.request.user, "project", "read", Project.objects.select_related("owner")
        )

    def perform_create(self, serializer):
        project = serializer.save(owner=self.request.user)
        logger.info("Project created: %s (owner=%s)", project.name, project.owner.email)


class ProjectDetailView(APIView):
    """
    GET    /api/projects/{id}/  — project detail
    PATCH  /api/projects/{id}/  — update project
    DELETE /api/projects/{id}/  — delete project
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "project"
    rbac_action = "auto"

    def get_rbac_owner_id(self, request: Request, obj: Project) -> int:
        return obj.owner_id

    def _get_object(self, request: Request, pk: int) -> Project | None:
        try:
            obj = Project.objects.select_related("owner").get(pk=pk)
        except Project.DoesNotExist:
            return None
        self.check_object_permissions(request, obj)
        return obj

    def get(self, request: Request, pk: int) -> Response:
        obj = self._get_object(request, pk)
        if obj is None:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProjectSerializer(obj).data)

    def patch(self, request: Request, pk: int) -> Response:
        obj = self._get_object(request, pk)
        if obj is None:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProjectSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProjectSerializer(obj).data)

    def delete(self, request: Request, pk: int) -> Response:
        obj = self._get_object(request, pk)
        if obj is None:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        