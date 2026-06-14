import logging

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.schema import DetailResponseSerializer, ErrorResponseSerializer
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

    @extend_schema(responses=UserProfileSerializer)
    def get(self, request: Request) -> Response:
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(request=UserUpdateSerializer, responses=UserProfileSerializer)
    def patch(self, request: Request) -> Response:
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserProfileSerializer(request.user).data)

    @extend_schema(
        request=inline_serializer(
            name="SoftDeleteRequest",
            fields={"refresh": serializers.CharField(required=False)},
        ),
        responses={200: DetailResponseSerializer},
    )
    def delete(self, request: Request) -> Response:
        """
        Soft-delete: sets is_active=False and blacklists the refresh token.
        User will not be able to log in again, but the record stays in DB.
        """
        user = request.user

        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
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

    @extend_schema(operation_id="users_list", responses=UserListSerializer(many=True))
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

    @extend_schema(responses={200: UserProfileSerializer, 404: ErrorResponseSerializer})
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
        