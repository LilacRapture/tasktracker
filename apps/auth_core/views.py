import logging
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import LoginSerializer, LogoutSerializer, RegisterSerializer, UserBriefSerializer

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """
    POST /api/auth/register/

    Public endpoint. Creates a new user account.
    Returns user data and JWT token pair so the user is immediately logged in.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens so user is logged in right after registration
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserBriefSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/auth/login/

    Public endpoint. Validates credentials and returns JWT token pair.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        user = data["user"]

        return Response(
            {
                "user": UserBriefSerializer(user).data,
                "access": data["access"],
                "refresh": data["refresh"],
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/

    Protected endpoint. Blacklists the refresh token.
    The client should also discard the access token locally.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(TokenRefreshView):
    """
    POST /api/auth/refresh/

    Public endpoint. Returns a new access token given a valid refresh token.
    Inherits from SimpleJWT's TokenRefreshView — no custom logic needed.
    Subclassed here so it lives under our urls and can be extended later.
    """
    pass
