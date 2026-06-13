import logging

from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class Role(models.Model):
    """
    Named group that bundles access rules.
    Examples: admin, manager, developer, viewer.
    """

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rbac_role"
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class UserRole(models.Model):
    """
    Which roles a user has. Many-to-many with audit fields.
    A user can have multiple roles simultaneously.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_roles",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_roles",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_roles",
        help_text="User who granted this role. Null if assigned via seed/system.",
    )

    class Meta:
        db_table = "rbac_userrole"
        verbose_name = "User Role"
        verbose_name_plural = "User Roles"
        # One user can't have the same role twice
        unique_together = [("user", "role")]

    def __str__(self) -> str:
        return f"{self.user} → {self.role}"


class AccessRule(models.Model):
    """
    One row = one role's permissions on one resource.

    Ownership-aware: _all flags apply to any object of this resource,
    plain flags apply only when the requesting user owns the object
    (i.e. obj.owner_id == request.user.id).

    Unique constraint: (role, resource) — one rule set per role per resource.
    """

    RESOURCE_CHOICES = [
        ("task", "Task"),
        ("project", "Project"),
        ("user", "User"),
        ("role", "Role"),
        ("access_rule", "Access Rule"),
    ]

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="access_rules",
    )
    resource = models.CharField(max_length=50, choices=RESOURCE_CHOICES)

    # Read
    can_read = models.BooleanField(
        default=False,
        help_text="Can read objects owned by self.",
    )
    can_read_all = models.BooleanField(
        default=False,
        help_text="Can read any object of this resource.",
    )

    # Create
    can_create = models.BooleanField(
        default=False,
        help_text="Can create new objects of this resource.",
    )

    # Update
    can_update = models.BooleanField(
        default=False,
        help_text="Can update objects owned by self.",
    )
    can_update_all = models.BooleanField(
        default=False,
        help_text="Can update any object of this resource.",
    )

    # Delete
    can_delete = models.BooleanField(
        default=False,
        help_text="Can delete objects owned by self.",
    )
    can_delete_all = models.BooleanField(
        default=False,
        help_text="Can delete any object of this resource.",
    )

    class Meta:
        db_table = "rbac_accessrule"
        verbose_name = "Access Rule"
        verbose_name_plural = "Access Rules"
        # One rule set per role per resource — no duplicates
        unique_together = [("role", "resource")]

    def __str__(self) -> str:
        return f"{self.role.name} / {self.resource}"
