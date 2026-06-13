from django.contrib import admin
from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "owner", "project", "due_date", "created_at"]
    list_filter = ["status"]
    search_fields = ["title", "owner__email"]
    