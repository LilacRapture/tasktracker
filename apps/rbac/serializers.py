from rest_framework import serializers

from .models import AccessRule, Role, UserRole


class AccessRuleSerializer(serializers.ModelSerializer):
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
    access_rules = AccessRuleSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = ["id", "name", "description", "created_at", "access_rules"]
        read_only_fields = ["id", "created_at"]


class RoleCreateUpdateSerializer(serializers.ModelSerializer):
    """Write serializer; access rules are managed through their own endpoints."""

    class Meta:
        model = Role
        fields = ["id", "name", "description"]
        read_only_fields = ["id"]


class AccessRuleCreateUpdateSerializer(serializers.ModelSerializer):
    """`role` is set by the view from the URL, not from the request body."""

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
    role_name = serializers.CharField(source="role.name", read_only=True)
    assigned_by_email = serializers.CharField(
        source="assigned_by.email", read_only=True, default=None
    )

    class Meta:
        model = UserRole
        fields = ["id", "role", "role_name", "assigned_at", "assigned_by_email"]
        read_only_fields = ["id", "assigned_at", "assigned_by_email"]


class AssignRoleSerializer(serializers.Serializer):
    """Assigns a role to a user; unknown roles and duplicates are rejected."""

    # Needs `user` in the serializer context.
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
