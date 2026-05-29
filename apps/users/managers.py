import logging
from django.contrib.auth.models import BaseUserManager

logger = logging.getLogger(__name__)


class UserManager(BaseUserManager):
    """
    Custom manager for User model where email is the unique identifier
    instead of username.
    """

    def create_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        middle_name: str = "",
        **extra_fields,
    ) -> "User":
        """Create and return a regular user."""
        if not email:
            raise ValueError("Email is required")
        if not password:
            raise ValueError("Password is required")
        if not first_name or not last_name:
            raise ValueError("First name and last name are required")

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            **extra_fields,
        )
        user.set_password(password)  # hashes the password
        user.save(using=self._db)
        logger.info("Created new user: %s", email)
        return user

    def create_superuser(
        self,
        email: str,
        password: str,
        first_name: str = "Admin",
        last_name: str = "User",
        **extra_fields,
    ) -> "User":
        """Create and return a superuser (for Django admin access)."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, first_name, last_name, **extra_fields)
