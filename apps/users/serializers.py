import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()
logger = logging.getLogger(__name__)


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "middle_name",
            "full_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UserUpdateSerializer(serializers.ModelSerializer):
    """Own-profile update: names only. Email and password can't be changed here."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "middle_name"]

    def update(self, instance: User, validated_data: dict) -> User:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(update_fields=[*validated_data.keys(), "updated_at"])
        logger.info("User profile updated: %s", instance.email)
        return instance


class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "is_active", "created_at"]
