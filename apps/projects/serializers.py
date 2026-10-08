from rest_framework import serializers

from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    """`owner` is read-only: it's the caller on create."""

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "status",
            "owner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]
