import django_filters

from .models import Project


class ProjectFilter(django_filters.FilterSet):
    """
    Filters for GET /api/projects/.

    - status: exact match (planned / active / completed / archived)
    - owner: exact match by user id
    """

    class Meta:
        model = Project
        fields = ["status", "owner"]
        