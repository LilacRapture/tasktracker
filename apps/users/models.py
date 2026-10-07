import logging

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager

logger = logging.getLogger(__name__)


class User(AbstractBaseUser, PermissionsMixin):
    """Email-login user. `is_active=False` means soft-deleted (ADR-004).

    `PermissionsMixin` exists for Django admin only; API access goes through apps/rbac (ADR-001).
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

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"

    @property
    def full_name(self) -> str:
        """Formatted as 'Last First Middle'."""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)

    @property
    def short_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self) -> str:
        return self.full_name

    def get_short_name(self) -> str:
        return self.short_name

    def soft_delete(self) -> None:
        """Deactivate without removing the record; the caller blacklists the user's tokens."""
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])
        logger.info("User soft-deleted: %s (id=%s)", self.email, self.pk)
