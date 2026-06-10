import logging
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rbac.permissions import RBACPermission
from .models import AccessRule, Role, UserRole
from .serializers import (
    AccessRuleCreateUpdateSerializer,
    AccessRuleSerializer,
    AssignRoleSerializer,
    RoleCreateUpdateSerializer,
    RoleSerializer,
    UserRoleSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

class RoleListView(APIView):
    """
    GET  /api/rbac/roles/  — list all roles
    POST /api/rbac/roles/  — create a new role
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "role"
    rbac_action = "auto"

    def get(self, request: Request) -> Response:
        roles = Role.objects.prefetch_related("access_rules").all()
        return Response(RoleSerializer(roles, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = RoleCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)


class RoleDetailView(APIView):
    """
    GET    /api/rbac/roles/{id}/  — role detail
    PATCH  /api/rbac/roles/{id}/  — update role name/description
    DELETE /api/rbac/roles/{id}/  — delete role
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "role"
    rbac_action = "auto"

    def _get_role(self, pk: int) -> Role | None:
        try:
            return Role.objects.prefetch_related("access_rules").get(pk=pk)
        except Role.DoesNotExist:
            return None

    def get(self, request: Request, pk: int) -> Response:
        role = self._get_role(pk)
        if not role:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(RoleSerializer(role).data)

    def patch(self, request: Request, pk: int) -> Response:
        role = self._get_role(pk)
        if not role:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = RoleCreateUpdateSerializer(role, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(RoleSerializer(role).data)

    def delete(self, request: Request, pk: int) -> Response:
        role = self._get_role(pk)
        if not role:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Access Rules per Role
# ---------------------------------------------------------------------------

class AccessRuleListView(APIView):
    """
    GET  /api/rbac/roles/{role_id}/rules/  — list access rules for a role
    POST /api/rbac/roles/{role_id}/rules/  — create access rule for a resource
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "access_rule"
    rbac_action = "auto"

    def _get_role(self, role_id: int) -> Role | None:
        try:
            return Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            return None

    def get(self, request: Request, role_id: int) -> Response:
        role = self._get_role(role_id)
        if not role:
            return Response({"error": "Role not found"}, status=status.HTTP_404_NOT_FOUND)
        rules = AccessRule.objects.filter(role=role)
        return Response(AccessRuleSerializer(rules, many=True).data)

    def post(self, request: Request, role_id: int) -> Response:
        role = self._get_role(role_id)
        if not role:
            return Response({"error": "Role not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = AccessRuleCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resource = serializer.validated_data["resource"]
        if AccessRule.objects.filter(role=role, resource=resource).exists():
            return Response(
                {"error": f"AccessRule for resource '{resource}' already exists for this role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rule = serializer.save(role=role)
        return Response(AccessRuleSerializer(rule).data, status=status.HTTP_201_CREATED)


class AccessRuleDetailView(APIView):
    """
    PATCH  /api/rbac/roles/{role_id}/rules/{resource}/  — update rule booleans
    DELETE /api/rbac/roles/{role_id}/rules/{resource}/  — remove rule entirely
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "access_rule"
    rbac_action = "auto"

    def _get_rule(self, role_id: int, resource: str) -> AccessRule | None:
        try:
            return AccessRule.objects.get(role_id=role_id, resource=resource)
        except AccessRule.DoesNotExist:
            return None

    def patch(self, request: Request, role_id: int, resource: str) -> Response:
        rule = self._get_rule(role_id, resource)
        if not rule:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AccessRuleCreateUpdateSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AccessRuleSerializer(rule).data)

    def delete(self, request: Request, role_id: int, resource: str) -> Response:
        rule = self._get_rule(role_id, resource)
        if not rule:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# User Role Assignment
# ---------------------------------------------------------------------------

class UserRoleListView(APIView):
    """
    GET  /api/users/{user_id}/roles/  — list roles assigned to a user
    POST /api/users/{user_id}/roles/  — assign a role to a user
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "role"
    rbac_action = "auto"

    def _get_user(self, user_id: int):
        try:
            return User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None

    def get(self, request: Request, user_id: int) -> Response:
        user = self._get_user(user_id)
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        user_roles = UserRole.objects.filter(user=user).select_related("role", "assigned_by")
        return Response(UserRoleSerializer(user_roles, many=True).data)

    def post(self, request: Request, user_id: int) -> Response:
        user = self._get_user(user_id)
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = AssignRoleSerializer(
            data=request.data,
            context={"user": user},
        )
        serializer.is_valid(raise_exception=True)

        user_role = UserRole.objects.create(
            user=user,
            role_id=serializer.validated_data["role_id"],
            assigned_by=request.user,
        )
        return Response(
            UserRoleSerializer(user_role).data,
            status=status.HTTP_201_CREATED,
        )


class UserRoleDetailView(APIView):
    """
    DELETE /api/users/{user_id}/roles/{role_id}/  — remove a role from a user
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "role"
    rbac_action = "auto"

    def delete(self, request: Request, user_id: int, role_id: int) -> Response:
        try:
            user_role = UserRole.objects.get(user_id=user_id, role_id=role_id)
        except UserRole.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        user_role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
