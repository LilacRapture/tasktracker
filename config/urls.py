from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.auth_core.urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/rbac/", include("apps.rbac.urls")),
    path("api/tasks/", include("apps.tasks.urls")),
    path("api/projects/", include("apps.projects.urls")),
]
