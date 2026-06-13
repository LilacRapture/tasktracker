import logging

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager

logger = logging.getLogger(__name__)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model. Email is the login identifier, not username.

    Profile and auth fields:
      - first_name, last_name, middle_name
      - email (unique login)
      - password (stored as hash via AbstractBaseUser)
      - is_active — False means soft-deleted: user cannot log in,
        but the record is preserved in the DB

    AbstractBaseUser provides:
      - password field + set_password() / check_password()
      - last_login field
      - is_active field

    PermissionsMixin provides:
      - is_superuser, groups, user_permissions
      - has_perm(), has_module_perms() — used only by Django admin,
        NOT used by the custom RBAC system
    """

    email = models.EmailField(unique=True, db_index=True)

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, default="")

    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Designates whether this user account is active. "
            "Set to False instead of deleting the account (soft delete)."
        ),
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Grants access to Django admin interface.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Tell Django to use our custom manager
    objects = UserManager()

    # The field used as the login identifier
    USERNAME_FIELD = "email"

    # Fields prompted when using createsuperuser (besides email+password)
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"

    # --- Properties ---

    @property
    def full_name(self) -> str:
        """Return full name in 'Last First Middle' format."""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)

    @property
    def short_name(self) -> str:
        """Return 'First Last' — used in some Django internals."""
        return f"{self.first_name} {self.last_name}"

    # --- Required by AbstractBaseUser ---

    def get_full_name(self) -> str:
        return self.full_name

    def get_short_name(self) -> str:
        return self.short_name

    # --- Soft delete ---

    def soft_delete(self) -> None:
        """
        Deactivate account without removing the DB record.
        The caller is responsible for logging the user out (blacklisting token).
        """
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])
        logger.info("User soft-deleted: %s (id=%s)", self.email, self.pk)
