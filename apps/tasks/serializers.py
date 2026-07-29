import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.projects.models import Project
from apps.realtime.broadcaster import broadcast_task_event

from .models import Task

User = get_user_model()
logger = logging.getLogger(__name__)


class OwnerBriefSerializer(serializers.ModelSerializer):
    """Minimal user representation nested inside Task responses."""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name"]


class ProjectBriefSerializer(serializers.ModelSerializer):
    """Minimal project representation nested inside Task responses."""

    class Meta:
        model = Project
        fields = ["id", "name"]


class TaskSerializer(serializers.ModelSerializer):
    """
    Read serializer for tasks. Nests owner and project as brief objects.
    Use TaskWriteSerializer for create/update.
    """

    owner = OwnerBriefSerializer(read_only=True)
    project = ProjectBriefSerializer(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "due_date",
            "owner",
            "project",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TaskWriteSerializer(serializers.ModelSerializer):
    """
    Write serializer for create/update. `project` accepts a project id
    (or null). `owner` is set by the view from request.user — not
    accepted from the client.
    """

    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "status",
            "due_date",
            "project",
        ]

    def create(self, validated_data: dict) -> Task:
        validated_data["owner"] = self.context["request"].user
        task = Task.objects.create(**validated_data)
        logger.info("Task created: %s (owner=%s)", task.title, task.owner.email)
        broadcast_task_event(task, "task.created")
        return task

    def update(self, instance: Task, validated_data: dict) -> Task:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(update_fields=[*validated_data.keys(), "updated_at"])
        logger.info("Task updated: %s (id=%s)", instance.title, instance.pk)
        broadcast_task_event(instance, "task.updated")
        return instance
        