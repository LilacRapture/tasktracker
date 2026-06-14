import django_filters

from .models import Task


class TaskFilter(django_filters.FilterSet):
    """
    Filters for GET /api/tasks/.

    - status: exact match (todo / in_progress / done)
    - project: exact match by project id
    - owner: exact match by user id
    - due_date: exact match
    - due_date_after / due_date_before: range on due_date
    """

    due_date_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")
    due_date_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")

    class Meta:
        model = Task
        fields = ["status", "project", "owner", "due_date"]
        