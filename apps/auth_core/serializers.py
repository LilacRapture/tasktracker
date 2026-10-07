import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .tokens import generate_jwt_pair

User = get_user_model()
logger = logging.getLogger(__name__)


class RegisterSerializer(serializers.ModelSerializer):
    """Creates a user account; `password` must match `password_confirm`."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "middle_name",
        ]

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data: dict) -> User:
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        logger.info("Registered new user: %s", user.email)
        return user


class LoginSerializer(serializers.Serializer):
    """Validates credentials; returns the user with a JWT pair."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        email = attrs["email"].lower().strip()
        password = attrs["password"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Same message for "no user" and "wrong password" so registered emails don't leak.
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid email or password."]}
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid email or password."]}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"non_field_errors": ["This account has been deactivated."]}
            )

        tokens = generate_jwt_pair(user)

        logger.info("User logged in: %s", user.email)

        return {
            "user": user,
            **tokens,
        }


class LogoutSerializer(serializers.Serializer):
    """Blacklists the given refresh token. The access token stays valid until it expires."""

    refresh = serializers.CharField()

    def validate(self, attrs: dict) -> dict:
        self.token = attrs["refresh"]
        return attrs

    def save(self, **kwargs) -> None:
        try:
            token = RefreshToken(self.token)
            token.blacklist()
            logger.info("Refresh token blacklisted")
        except Exception:
            raise serializers.ValidationError({"refresh": "Token is invalid or already blacklisted."})


class UserBriefSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "created_at"]
