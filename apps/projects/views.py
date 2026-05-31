import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rbac.permissions import RBACPermission

logger = logging.getLogger(__name__)

# Mock data — will be replaced with real Project model in Phase 2
MOCK_PROJECTS = [
    {
        "id": 1,
        "name": "TaskTracker Backend",
        "description": "Custom auth + RBAC system with DRF",
        "owner_id": 1,
        "status": "active",
    },
    {
        "id": 2,
        "name": "Portfolio Site",
        "description": "Personal portfolio and blog",
        "owner_id": 2,
        "status": "planned",
    },
]


class ProjectListView(APIView):
    """
    GET  /api/projects/  — list mock projects (requires project:read)
    POST /api/projects/  — create mock project (requires project:create)

    Phase 1: returns hardcoded data to demonstrate RBAC works.
    Phase 2: will use real Project model with full CRUD.
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "project"
    rbac_action = "read"

    def get(self, request: Request) -> Response:
        return Response(MOCK_PROJECTS)

    def post(self, request: Request) -> Response:
        from apps.rbac.permissions import check_access
        if not check_access(request.user, "project", "create"):
            return Response(
                {"error": "Permission denied. Required: project:create"},
                status=403,
            )

        mock_created = {
            "id": 99,
            "name": request.data.get("name", "New project"),
            "description": request.data.get("description", ""),
            "owner_id": request.user.pk,
            "status": "planned",
        }
        logger.info("Mock project created by user %s", request.user.email)
        return Response(mock_created, status=201)
