import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rbac.permissions import RBACPermission

logger = logging.getLogger(__name__)

# Mock data — will be replaced with real Task model in Phase 2
MOCK_TASKS = [
    {
        "id": 1,
        "title": "Set up project repository",
        "description": "Initialize git repo, configure CI/CD pipeline",
        "status": "done",
        "owner_id": 1,
    },
    {
        "id": 2,
        "title": "Design database schema",
        "description": "ERD for tasks, projects, comments",
        "status": "in_progress",
        "owner_id": 2,
    },
    {
        "id": 3,
        "title": "Implement auth endpoints",
        "description": "Register, login, logout, token refresh",
        "status": "in_progress",
        "owner_id": 2,
    },
]


class TaskListView(APIView):
    """
    GET  /api/tasks/  — list mock tasks (requires task:read)
    POST /api/tasks/  — create mock task (requires task:create)

    Phase 1: returns hardcoded data to demonstrate RBAC works.
    Phase 2: will use real Task model with full CRUD.
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "task"
    rbac_action = "read"

    def get(self, request: Request) -> Response:
        return Response(MOCK_TASKS)

    def post(self, request: Request) -> Response:
        from apps.rbac.permissions import check_access
        if not check_access(request.user, "task", "create"):
            return Response(
                {"error": "Permission denied. Required: task:create"},
                status=403,
            )

        # Mock response — pretend we created a task
        mock_created = {
            "id": 99,
            "title": request.data.get("title", "New task"),
            "description": request.data.get("description", ""),
            "status": "todo",
            "owner_id": request.user.pk,
        }
        logger.info("Mock task created by user %s", request.user.email)
        return Response(mock_created, status=201)
