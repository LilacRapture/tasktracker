import logging
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Role, AccessRule, UserRole

User = get_user_model()
logger = logging.getLogger(__name__)


class AccessRuleSerializer(serializers.ModelSerializer):
    """
    Serializes AccessRule — the boolean permission flags for a role+resource pair.
    """

    class Meta:
        model = AccessRule
        fields = [
            "id",
            "resource",
            "can_read",
            "can_read_all",
            "can_create",
            "can_update",
            "can_update_all",
            "can_delete",
            "can_delete_all",
        ]


class RoleSerializer(serializers.ModelSerializer):
    """
    Full role representation including its access rules.
    """

    access_rules = AccessRuleSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = ["id", "name", "description", "created_at", "access_rules"]
        read_only_fields = ["id", "created_at"]


class RoleCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Used for creating and updating roles (without nested access_rules).
    """

    class Meta:
        model = Role
        fields = ["id", "name", "description"]
        read_only_fields = ["id"]


class AccessRuleCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Used for creating or updating an AccessRule for a role+resource pair.
    role is set by the view from the URL, not from request body.
    """

    class Meta:
        model = AccessRule
        fields = [
            "resource",
            "can_read",
            "can_read_all",
            "can_create",
            "can_update",
            "can_update_all",
            "can_delete",
            "can_delete_all",
        ]


class UserRoleSerializer(serializers.ModelSerializer):
    """
    Represents a role assignment for a user.
    Used for GET /users/{id}/roles/
    """

    role_name = serializers.CharField(source="role.name", read_only=True)
    assigned_by_email = serializers.CharField(
        source="assigned_by.email", read_only=True, default=None
    )

    class Meta:
        model = UserRole
        fields = ["id", "role", "role_name", "assigned_at", "assigned_by_email"]
        read_only_fields = ["id", "assigned_at", "assigned_by_email"]


class AssignRoleSerializer(serializers.Serializer):
    """
    Used for POST /users/{id}/roles/ — assign a role to a user.
    Accepts role_id, validates it exists, checks for duplicates.
    """

    role_id = serializers.IntegerField()

    def validate_role_id(self, value: int) -> int:
        if not Role.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Role does not exist.")
        return value

    def validate(self, attrs: dict) -> dict:
        user = self.context["user"]
        role_id = attrs["role_id"]
        if UserRole.objects.filter(user=user, role_id=role_id).exists():
            raise serializers.ValidationError(
                {"role_id": "This role is already assigned to the user."}
            )
        return attrs
