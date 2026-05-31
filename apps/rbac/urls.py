from django.urls import path
from .views import (
    RoleListView,
    RoleDetailView,
    AccessRuleListView,
    AccessRuleDetailView,
    UserRoleListView,
    UserRoleDetailView,
)

urlpatterns = [
    # Roles
    path("roles/", RoleListView.as_view(), name="rbac-role-list"),
    path("roles/<int:pk>/", RoleDetailView.as_view(), name="rbac-role-detail"),

    # Access rules per role
    path("roles/<int:role_id>/rules/", AccessRuleListView.as_view(), name="rbac-rule-list"),
    path("roles/<int:role_id>/rules/<str:resource>/", AccessRuleDetailView.as_view(), name="rbac-rule-detail"),
]

# User role assignment urls live in apps/users/urls.py
