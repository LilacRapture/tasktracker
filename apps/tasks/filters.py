import django_filters

from .models import Task


class TaskFilter(django_filters.FilterSet):
    due_date_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")
    due_date_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")

    class Meta:
        model = Task
        fields = ["status", "project", "owner", "due_date"]
