import logging

from django.contrib.postgres.aggregates import BoolOr
from django.db.models import Q
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from .models import AccessRule, UserRole

logger = logging.getLogger(__name__)


def _user_role_ids(user):
    return UserRole.objects.filter(user=user).values_list("role_id", flat=True)


def has_any_access(user, resource: str, action: str) -> bool:
    """
    List/create-level gate.

    Returns True if the user has ANY relevant flag for (resource, action) —
    i.e. can_{action} OR can_{action}_all for read/update/delete,
    or can_create for create.

    This does NOT determine *which* objects the user can see/modify —
    that's get_accessible_queryset()'s job. This only answers
    "is this endpoint reachable at all for this user".
    """
    if not user or not user.is_active:
        return False

    user_role_ids = _user_role_ids(user)
    if not user_role_ids:
        logger.debug("has_any_access: user %s has no roles", user.email)
        return False

    rules = AccessRule.objects.filter(role_id__in=user_role_ids, resource=resource)

    if action == "create":
        return rules.filter(can_create=True).exists()

    own_field = f"can_{action}"
    all_field = f"can_{action}_all"
    return rules.filter(Q(**{own_field: True}) | Q(**{all_field: True})).exists()


def check_access(
    user,
    resource: str,
    action: str,
    obj_owner_id: int | None = None,
) -> bool:
    """
    Object-level RBAC check. Returns True if user may perform action on
    a SPECIFIC object (or on the resource generally for create).

    Args:
        user:         the requesting User instance
        resource:     resource string — "task", "project", "user", "role", "access_rule"
        action:       "read" | "create" | "update" | "delete"
        obj_owner_id: pk of the object's owner, if known (for ownership checks)

    Logic:
        - create: checks can_create only (no ownership concept)
        - read/update/delete: checks can_{action}_all first (global access),
          then can_{action} if obj_owner_id == user.id (own objects only)

    Note: for list/create endpoints without a specific object, use
    has_any_access() instead — this function requires obj_owner_id to
    grant own-object access.
    """
    if not user or not user.is_active:
        return False

    user_role_ids = _user_role_ids(user)
    if not user_role_ids:
        logger.debug("check_access: user %s has no roles", user.email)
        return False

    rules = AccessRule.objects.filter(role_id__in=user_role_ids, resource=resource)

    if action == "create":
        result = rules.filter(can_create=True).exists()
        logger.debug(
            "check_access: user=%s resource=%s action=create → %s",
            user.email, resource, result,
        )
        return result

    all_field = f"can_{action}_all"
    own_field = f"can_{action}"

    if rules.filter(**{all_field: True}).exists():
        logger.debug(
            "check_access: user=%s resource=%s action=%s → True (all)",
            user.email, resource, action,
        )
        return True

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


def get_accessible_queryset(user, resource: str, action: str, queryset):
    """
    Filter a queryset according to the user's AccessRule flags for
    (resource, action).

    Returns:
        - the full queryset if the user has can_{action}_all
        - queryset filtered to owner=user if the user has can_{action} only
        - an empty queryset if neither flag is granted

    Assumes the queryset's model has an `owner` FK to AUTH_USER_MODEL.
    Mirrors the precedence in check_access(): _all wins over own.

    Typically called AFTER has_any_access() has already gated the request
    at has_permission() — this function narrows WHICH rows are visible.
    """
    if not user or not user.is_active:
        return queryset.none()

    user_role_ids = _user_role_ids(user)
    if not user_role_ids:
        return queryset.none()

    rules = AccessRule.objects.filter(role_id__in=user_role_ids, resource=resource)

    all_field = f"can_{action}_all"
    own_field = f"can_{action}"

    if rules.filter(**{all_field: True}).exists():
        return queryset

    if rules.filter(**{own_field: True}).exists():
        return queryset.filter(owner=user)

    return queryset.none()


def _empty_capabilities() -> dict:
    return {
        "can_read": False,
        "can_read_all": False,
        "can_create": False,
        "can_update": False,
        "can_update_all": False,
        "can_delete": False,
        "can_delete_all": False,
    }


def get_user_capabilities(user) -> dict:
    """
    Merged (OR'd across all of the user's roles) AccessRule flags per
    resource — the same underlying data has_any_access()/check_access()
    query, just exposed as a read-only view of "what can I do" rather
    than a permission gate. Used by GET /api/users/me/capabilities/ so
    the frontend can derive its own UI visibility without needing to
    know role names (see that endpoint's docstring for the full
    rationale — avoids duplicating RBAC precedence logic client-side).

    Uses Postgres's BOOL_OR aggregate to merge across roles in a
    single query rather than iterating roles in Python.
    """
    result = {resource: _empty_capabilities() for resource, _ in AccessRule.RESOURCE_CHOICES}

    if not user or not user.is_active:
        return result

    user_role_ids = _user_role_ids(user)
    if not user_role_ids:
        return result

    rows = (
        AccessRule.objects.filter(role_id__in=user_role_ids)
        .values("resource")
        .annotate(
            can_read=BoolOr("can_read"),
            can_read_all=BoolOr("can_read_all"),
            can_create=BoolOr("can_create"),
            can_update=BoolOr("can_update"),
            can_update_all=BoolOr("can_update_all"),
            can_delete=BoolOr("can_delete"),
            can_delete_all=BoolOr("can_delete_all"),
        )
    )

    for row in rows:
        result[row["resource"]] = {k: v for k, v in row.items() if k != "resource"}

    return result


class RBACPermission(BasePermission):
    """
    DRF permission class that enforces the custom RBAC system.

    Views that use this class must declare:
        rbac_resource = "task"           # which resource is being accessed
        rbac_action   = "read"           # which action is being performed,
                                          # or "auto" to derive from HTTP method

    Two-layer enforcement:
        - has_permission(): endpoint-level gate via has_any_access().
          "Can this user reach this endpoint at all?"
        - has_object_permission(): object-level check via check_access(),
          using the object's owner_id for ownership-aware decisions.

    For list endpoints, views should additionally call
    get_accessible_queryset() to filter rows — has_permission() alone
    does not restrict to "own" objects.

    Usage:
        class TaskListView(APIView):
            permission_classes = [IsAuthenticated, RBACPermission]
            rbac_resource = "task"
            rbac_action = "auto"

            def get(self, request):
                qs = get_accessible_queryset(request.user, "task", "read", Task.objects.all())
                ...

        class TaskDetailView(APIView):
            permission_classes = [IsAuthenticated, RBACPermission]
            rbac_resource = "task"
            rbac_action = "auto"

            def get_rbac_owner_id(self, request, **kwargs):
                task = Task.objects.get(pk=self.kwargs["pk"])
                return task.owner_id
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """
        Called on every request before the view runs.

        Endpoint-level gate: does the user have ANY can_{action} or
        can_{action}_all flag for this resource? Does not check ownership —
        that's handled by get_accessible_queryset() (lists) or
        has_object_permission() (detail views).
        """
        resource = getattr(view, "rbac_resource", None)
        action = getattr(view, "rbac_action", None)

        if not resource or not action:
            logger.warning(
                "RBACPermission: view %s missing rbac_resource or rbac_action — denying",
                view.__class__.__name__,
            )
            return False

        if action == "auto":
            action = self._method_to_action(request.method)

        result = has_any_access(request.user, resource, action)

        if not result:
            self.message = (
                f"Permission denied. Required: {resource}:{action}"
            )

        return result

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        """
        Called after has_permission when accessing a specific object.
        Passes the object's owner_id for ownership-aware checks via check_access().
        """
        resource = getattr(view, "rbac_resource", None)
        action = getattr(view, "rbac_action", None)

        if not resource or not action:
            return False

        if action == "auto":
            action = self._method_to_action(request.method)

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
        get_owner = getattr(view, "get_rbac_owner_id", None)
        if callable(get_owner):
            return get_owner(request, obj)

        if hasattr(obj, "owner_id"):
            return obj.owner_id

        if hasattr(obj, "creator_id"):
            return obj.creator_id

        return None