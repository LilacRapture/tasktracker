import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .tokens import generate_jwt_pair

User = get_user_model()
logger = logging.getLogger(__name__)


class RegisterSerializer(serializers.ModelSerializer):
    """
    Validates and creates a new user account.

    Accepts: email, password, password_confirm, first_name, last_name, middle_name
    Returns: user data (no password)
    """

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
        """Check that both passwords match."""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data: dict) -> User:
        """Remove password_confirm and create user via manager."""
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)  # hashes via AbstractBaseUser
        user.save()

        logger.info("Registered new user: %s", user.email)
        return user


class LoginSerializer(serializers.Serializer):
    """
    Validates login credentials and returns JWT token pair.

    Accepts: email, password
    Returns: access token, refresh token, basic user info
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        email = attrs["email"].lower().strip()
        password = attrs["password"]

        # Look up user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Same error message for both "no user" and "wrong password"
            # to avoid leaking which emails are registered
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid email or password."]}
            )

        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid email or password."]}
            )

        # Soft-deleted users cannot log in
        if not user.is_active:
            raise serializers.ValidationError(
                {"non_field_errors": ["This account has been deactivated."]}
            )

        # Generate JWT pair
        tokens = generate_jwt_pair(user)

        logger.info("User logged in: %s", user.email)

        return {
            "user": user,
            **tokens,
        }


class LogoutSerializer(serializers.Serializer):
    """
    Accepts a refresh token and blacklists it.

    After this the refresh token can no longer be used to get new access tokens.
    The access token will expire naturally (15 min by default).
    """

    refresh = serializers.CharField()

    def validate(self, attrs: dict) -> dict:
        self.token = attrs["refresh"]
        return attrs

    def save(self, **kwargs) -> None:
        """Blacklist the refresh token."""
        try:
            token = RefreshToken(self.token)
            token.blacklist()
            logger.info("Refresh token blacklisted")
        except Exception as e:
            raise serializers.ValidationError({"refresh": "Token is invalid or already blacklisted."})


class UserBriefSerializer(serializers.ModelSerializer):
    """
    Brief user representation returned after login/register.
    Never includes password.
    """

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "created_at"]
