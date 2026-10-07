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
    """Endpoint-level gate: any `can_{action}` / `can_{action}_all` flag (`can_create` for create).

    Says nothing about which objects are accessible — see `get_accessible_queryset()`.
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
    """Object-level check; algorithm in docs/rbac-schema.md.

    Own-object access needs `obj_owner_id`. For list/create without an object use `has_any_access()`.
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
    """Rows the user may `action`: all with `_all`, own (`owner=user`) with the plain flag, else none.

    Assumes an `owner` FK. Same precedence as `check_access()`.
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
    """AccessRule flags per resource, OR-merged across the user's roles.

    Lets clients gate UI without duplicating the precedence logic. One query via Postgres BOOL_OR.
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
    """DRF permission enforcing the custom RBAC (docs/rbac-schema.md).

    Views set `rbac_resource` and `rbac_action` ("auto" = from the HTTP method). List views must
    also narrow rows with `get_accessible_queryset()`; detail views get the owner from
    `get_rbac_owner_id()` or `obj.owner_id`.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
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
