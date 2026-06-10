import logging
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
logger = logging.getLogger(__name__)


def generate_jwt_pair(user: User) -> dict:
    """Generate access + refresh JWT pair for a user."""
    refresh = RefreshToken.for_user(user)
    logger.debug("Generated JWT pair for user %s", user.email)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }
