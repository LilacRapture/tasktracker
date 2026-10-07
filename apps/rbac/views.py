from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.schema import ErrorResponseSerializer
from apps.rbac.permissions import RBACPermission, get_user_capabilities

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


# --- Roles ---

class RoleListView(APIView):
    """List roles with their access rules, or create a role."""

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "role"
    rbac_action = "auto"

    @extend_schema(operation_id="rbac_roles_list", responses=RoleSerializer(many=True))
    def get(self, request: Request) -> Response:
        roles = Role.objects.prefetch_related("access_rules").all()
        return Response(RoleSerializer(roles, many=True).data)

    @extend_schema(request=RoleCreateUpdateSerializer, responses={201: RoleSerializer})
    def post(self, request: Request) -> Response:
        serializer = RoleCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)


class RoleDetailView(APIView):
    """Retrieve, update, or delete a role."""

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "role"
    rbac_action = "auto"

    def _get_role(self, pk: int) -> Role | None:
        try:
            return Role.objects.prefetch_related("access_rules").get(pk=pk)
        except Role.DoesNotExist:
            return None

    @extend_schema(responses={200: RoleSerializer, 404: ErrorResponseSerializer})
    def get(self, request: Request, pk: int) -> Response:
        role = self._get_role(pk)
        if not role:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(RoleSerializer(role).data)

    @extend_schema(
        request=RoleCreateUpdateSerializer,
        responses={200: RoleSerializer, 404: ErrorResponseSerializer},
    )
    def patch(self, request: Request, pk: int) -> Response:
        role = self._get_role(pk)
        if not role:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = RoleCreateUpdateSerializer(role, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(RoleSerializer(role).data)

    @extend_schema(responses={204: None, 404: ErrorResponseSerializer})
    def delete(self, request: Request, pk: int) -> Response:
        role = self._get_role(pk)
        if not role:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Access rules per role ---

class AccessRuleListView(APIView):
    """List or create access rules for a role (one rule per resource)."""

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "access_rule"
    rbac_action = "auto"

    def _get_role(self, role_id: int) -> Role | None:
        try:
            return Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            return None

    @extend_schema(responses={200: AccessRuleSerializer(many=True), 404: ErrorResponseSerializer})
    def get(self, request: Request, role_id: int) -> Response:
        role = self._get_role(role_id)
        if not role:
            return Response({"error": "Role not found"}, status=status.HTTP_404_NOT_FOUND)
        rules = AccessRule.objects.filter(role=role)
        return Response(AccessRuleSerializer(rules, many=True).data)

    @extend_schema(
        request=AccessRuleCreateUpdateSerializer,
        responses={
            201: AccessRuleSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
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
    """Update or delete a role's access rule for a resource."""

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "access_rule"
    rbac_action = "auto"

    def _get_rule(self, role_id: int, resource: str) -> AccessRule | None:
        try:
            return AccessRule.objects.get(role_id=role_id, resource=resource)
        except AccessRule.DoesNotExist:
            return None

    @extend_schema(
        request=AccessRuleCreateUpdateSerializer,
        responses={200: AccessRuleSerializer, 404: ErrorResponseSerializer},
    )
    def patch(self, request: Request, role_id: int, resource: str) -> Response:
        rule = self._get_rule(role_id, resource)
        if not rule:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AccessRuleCreateUpdateSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AccessRuleSerializer(rule).data)

    @extend_schema(responses={204: None, 404: ErrorResponseSerializer})
    def delete(self, request: Request, role_id: int, resource: str) -> Response:
        rule = self._get_rule(role_id, resource)
        if not rule:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- User role assignment ---

class UserRoleListView(APIView):
    """List the roles of a user, or assign a role to them."""

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "role"
    rbac_action = "auto"

    def _get_user(self, user_id: int):
        try:
            return User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None

    @extend_schema(responses={200: UserRoleSerializer(many=True), 404: ErrorResponseSerializer})
    def get(self, request: Request, user_id: int) -> Response:
        user = self._get_user(user_id)
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        user_roles = UserRole.objects.filter(user=user).select_related("role", "assigned_by")
        return Response(UserRoleSerializer(user_roles, many=True).data)

    @extend_schema(
        request=AssignRoleSerializer,
        responses={201: UserRoleSerializer, 404: ErrorResponseSerializer},
    )
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
    """Remove a role from a user."""

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "role"
    rbac_action = "auto"

    @extend_schema(responses={204: None, 404: ErrorResponseSerializer})
    def delete(self, request: Request, user_id: int, role_id: int) -> Response:
        try:
            user_role = UserRole.objects.get(user_id=user_id, role_id=role_id)
        except UserRole.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        user_role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Own capabilities ---

class MyCapabilitiesView(APIView):
    """Your role names and capability flags per resource, merged (OR) across roles, for UI gating."""

    # IsAuthenticated only: "read my own effective permissions" is not the `role` resource,
    # which /rbac/roles/ gates on. Same pattern as MeView.
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="MyCapabilitiesResponse",
                fields={
                    "roles": serializers.ListField(child=serializers.CharField()),
                    "capabilities": inline_serializer(
                        name="CapabilitiesByResource",
                        fields={
                            resource: inline_serializer(
                                name=f"{resource.title().replace('_', '')}Capabilities",
                                fields={
                                    "can_read": serializers.BooleanField(),
                                    "can_read_all": serializers.BooleanField(),
                                    "can_create": serializers.BooleanField(),
                                    "can_update": serializers.BooleanField(),
                                    "can_update_all": serializers.BooleanField(),
                                    "can_delete": serializers.BooleanField(),
                                    "can_delete_all": serializers.BooleanField(),
                                },
                            )
                            for resource, _ in AccessRule.RESOURCE_CHOICES
                        },
                    ),
                },
            ),
        },
    )
    def get(self, request: Request) -> Response:
        roles = list(
            Role.objects.filter(user_roles__user=request.user)
            .values_list("name", flat=True)
            .distinct()
        )
        return Response({
            "roles": roles,
            "capabilities": get_user_capabilities(request.user),
        })
