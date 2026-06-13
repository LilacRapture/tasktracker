from django.urls import path

from apps.rbac.views import UserRoleDetailView, UserRoleListView

from .views import MeView, UserDetailView, UserListView

urlpatterns = [
    path("me/", MeView.as_view(), name="user-me"),
    path("", UserListView.as_view(), name="user-list"),
    path("<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("<int:user_id>/roles/", UserRoleListView.as_view(), name="user-role-list"),
    path("<int:user_id>/roles/<int:role_id>/", UserRoleDetailView.as_view(), name="user-role-detail"),
]
