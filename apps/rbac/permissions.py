import logging
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView
from .models import UserRole, AccessRule

logger = logging.getLogger(__name__)


def check_access(
    user,
    resource: str,
    action: str,
    obj_owner_id: int | None = None,
) -> bool:
    """
    Core RBAC check. Returns True if user may perform action on resource.

    Args:
        user:         the requesting User instance
        resource:     resource string — "task", "project", "user", "role", "access_rule"
        action:       "read" | "create" | "update" | "delete"
        obj_owner_id: pk of the object's owner, if known (for ownership checks)

    Returns True if ANY of the user's roles grants access via AccessRule flags.

    Logic:
        - create: checks can_create only (no ownership concept)
        - read/update/delete: checks can_{action}_all first (global access),
          then can_{action} if obj_owner_id == user.id (own objects only)
    """
    if not user or not user.is_active:
        return False

    # Collect all role IDs the user has
    user_role_ids = UserRole.objects.filter(
        user=user
    ).values_list("role_id", flat=True)

    if not user_role_ids:
        logger.debug("check_access: user %s has no roles", user.email)
        return False

    # Get all AccessRule rows for those roles on this resource
    rules = AccessRule.objects.filter(
        role_id__in=user_role_ids,
        resource=resource,
    )

    if action == "create":
        result = rules.filter(can_create=True).exists()
        logger.debug(
            "check_access: user=%s resource=%s action=create → %s",
            user.email, resource, result,
        )
        return result

    # For read/update/delete: check _all first, then own-object
    all_field = f"can_{action}_all"  # e.g. "can_read_all"
    own_field = f"can_{action}"      # e.g. "can_read"

    # Global access — can act on ANY object of this resource
    if rules.filter(**{all_field: True}).exists():
        logger.debug(
            "check_access: user=%s resource=%s action=%s → True (all)",
            user.email, resource, action,
        )
        return True

    # Own-object access — can act only on objects the user created
    if obj_owner_id is not None and obj_owner_id == user.pk:
        result = rules.filter(**{own_field: True}).exists()
        logger.debug(
            "check_access: user=%s resource=%s action=%s → %s (own)",
            user.email, resource, action, result,
        )
        return result

    logger.debug(
        "check_access: user=%s resource=%s action=%s → False",
        user.email, resource, action,
    )
    return False


class RBACPermission(BasePermission):
    """
    DRF permission class that enforces the custom RBAC system.

    Views that use this class must declare:
        rbac_resource = "task"           # which resource is being accessed
        rbac_action   = "read"           # which action is being performed

    Optionally, for ownership-aware checks, the view can override
    get_rbac_owner_id() to return the owner's pk for the object being accessed.

    Usage:
        class TaskListView(APIView):
            permission_classes = [IsAuthenticated, RBACPermission]
            rbac_resource = "task"
            rbac_action = "read"

        class TaskDetailView(APIView):
            permission_classes = [IsAuthenticated, RBACPermission]
            rbac_resource = "task"
            rbac_action = "update"

            def get_rbac_owner_id(self, request, **kwargs):
                # called by RBACPermission to get the object owner
                task = Task.objects.get(pk=self.kwargs["pk"])
                return task.owner_id
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """
        Called on every request before the view runs.
        Checks resource+action access without object context.
        For ownership-aware checks use has_object_permission instead.
        """
        resource = getattr(view, "rbac_resource", None)
        action = getattr(view, "rbac_action", None)

        if not resource or not action:
            # View didn't declare RBAC requirements — deny by default
            logger.warning(
                "RBACPermission: view %s missing rbac_resource or rbac_action — denying",
                view.__class__.__name__,
            )
            return False

        # Map HTTP methods to actions when rbac_action is "auto"
        if action == "auto":
            action = self._method_to_action(request.method)

        result = check_access(request.user, resource, action)

        if not result:
            self.message = (
                f"Permission denied. Required: {resource}:{action}"
            )

        return result

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        """
        Called after has_permission when accessing a specific object.
        Passes the object's owner_id for ownership-aware checks.
        """
        resource = getattr(view, "rbac_resource", None)
        action = getattr(view, "rbac_action", None)

        if not resource or not action:
            return False

        if action == "auto":
            action = self._method_to_action(request.method)

        # Try to get owner_id from the object directly or via view hook
        owner_id = self._resolve_owner_id(request, view, obj)

        result = check_access(request.user, resource, action, obj_owner_id=owner_id)

        if not result:
            self.message = (
                f"Permission denied. Required: {resource}:{action}"
            )

        return result

    # --- Helpers ---

    @staticmethod
    def _method_to_action(method: str) -> str:
        """Map HTTP method to RBAC action string."""
        mapping = {
            "GET":    "read",
            "HEAD":   "read",
            "OPTIONS": "read",
            "POST":   "create",
            "PUT":    "update",
            "PATCH":  "update",
            "DELETE": "delete",
        }
        return mapping.get(method.upper(), "read")

    @staticmethod
    def _resolve_owner_id(request: Request, view: APIView, obj) -> int | None:
        """
        Try to resolve the owner pk of the object being accessed.

        Priority:
        1. view.get_rbac_owner_id(request, obj) — if view defines this hook
        2. obj.owner_id — direct attribute
        3. obj.creator_id — fallback attribute name
        4. None — ownership check skipped, only _all flags apply
        """
        # 1. View-defined hook (most flexible)
        get_owner = getattr(view, "get_rbac_owner_id", None)
        if callable(get_owner):
            return get_owner(request, obj)

        # 2. Direct attribute on the object
        if hasattr(obj, "owner_id"):
            return obj.owner_id

        # 3. Fallback attribute
        if hasattr(obj, "creator_id"):
            return obj.creator_id

        return None
