import logging
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.rbac.permissions import RBACPermission
from .serializers import UserListSerializer, UserProfileSerializer, UserUpdateSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class MeView(APIView):
    """
    GET  /api/users/me/    — get own profile
    PATCH /api/users/me/   — update own profile
    DELETE /api/users/me/  — soft-delete own account + logout
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request: Request) -> Response:
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserProfileSerializer(request.user).data)

    def delete(self, request: Request) -> Response:
        """
        Soft-delete: sets is_active=False and blacklists the refresh token.
        User will not be able to log in again, but the record stays in DB.
        """
        user = request.user

        # Blacklist the refresh token if provided
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                # Token already invalid — that's fine, we still delete the account
                pass

        user.soft_delete()

        return Response(
            {"detail": "Account deactivated successfully."},
            status=status.HTTP_200_OK,
        )


class UserListView(APIView):
    """
    GET /api/users/

    Returns list of all users.
    Requires: user:read (can_read_all — admin or manager level)
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "user"
    rbac_action = "read"

    def get(self, request: Request) -> Response:
        users = User.objects.filter(is_active=True)
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data)


class UserDetailView(APIView):
    """
    GET /api/users/{id}/

    Returns a specific user's profile.
    Requires: user:read
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "user"
    rbac_action = "read"

    def get(self, request: Request, pk: int) -> Response:
        try:
            user = User.objects.get(pk=pk, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)
