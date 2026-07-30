import logging
import secrets

from django.core.cache import cache
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.common.schema import DetailResponseSerializer
from apps.realtime.middleware import TICKET_CACHE_PREFIX

from .serializers import LoginSerializer, LogoutSerializer, RegisterSerializer, UserBriefSerializer
from .tokens import generate_jwt_pair

WS_TICKET_TTL_SECONDS = 20

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """
    POST /api/auth/register/

    Public endpoint. Creates a new user account.
    Returns user data and JWT token pair so the user is immediately logged in.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: inline_serializer(
                name="RegisterResponse",
                fields={
                    "user": UserBriefSerializer(),
                    "access": serializers.CharField(),
                    "refresh": serializers.CharField(),
                },
            ),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        tokens = generate_jwt_pair(user)

        return Response(
            {
                "user": UserBriefSerializer(user).data,
                **tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/auth/login/

    Public endpoint. Validates credentials and returns JWT token pair.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: inline_serializer(
                name="LoginResponse",
                fields={
                    "user": UserBriefSerializer(),
                    "access": serializers.CharField(),
                    "refresh": serializers.CharField(),
                },
            ),
        },
    )
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

    @extend_schema(
        request=LogoutSerializer,
        responses={200: DetailResponseSerializer},
    )
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


class WsTicketView(APIView):
    """
    POST /api/auth/ws-ticket/

    Protected endpoint. Issues a short-lived, single-use ticket for
    authenticating the WebSocket handshake (see docs/realtime.md,
    ADR-014) — browsers' native WebSocket API can't send an
    Authorization header, so this ticket travels in the connection URL
    instead of the raw access token.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="WsTicketResponse",
                fields={"ticket": serializers.CharField()},
            ),
        },
    )
    def post(self, request: Request) -> Response:
        ticket = secrets.token_urlsafe(32)
        cache.set(f"{TICKET_CACHE_PREFIX}{ticket}", request.user.pk, timeout=WS_TICKET_TTL_SECONDS)

        logger.info("WS ticket issued for user %s", request.user.email)

        return Response({"ticket": ticket}, status=status.HTTP_200_OK)
