import logging

from rest_framework import serializers

from .models import Project

logger = logging.getLogger(__name__)


class ProjectSerializer(serializers.ModelSerializer):
    """
    Full project representation. Used for list/detail (read) and
    create/update (write) — flat, no nested relations needed.

    `owner` is read-only; set from request.user on create.
    """

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
        