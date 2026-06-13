import pytest
from django.contrib.auth import get_user_model

from apps.rbac.management.commands.seed_roles import ACCESS_RULES
from apps.rbac.permissions import check_access, get_accessible_queryset, has_any_access
from apps.tasks.models import Task

User = get_user_model()

pytestmark = pytest.mark.django_db

ACTIONS = ["read", "create", "update", "delete"]


# ---------------------------------------------------------------------------
# Helpers — derive expected results directly from the seed ACCESS_RULES table
# ---------------------------------------------------------------------------

def _unpack(rule_tuple):
    """
    rule_tuple format (see seed_roles.py):
    (resource, can_read, can_read_all, can_create,
     can_update, can_update_all, can_delete, can_delete_all)
    """
    resource, r, ra, c, u, ua, d, da = rule_tuple
    return {
        "resource": resource,
        "create": c,
        "own": {"read": r, "update": u, "delete": d},
        "all": {"read": ra, "update": ua, "delete": da},
    }


def _expected_has_any(flags, action):
    if action == "create":
        return flags["create"]
    return flags["own"][action] or flags["all"][action]


def _all_cases():
    """One (role_name, rule_tuple, action) per row × action in ACCESS_RULES."""
    cases = []
    for role_name, rules in ACCESS_RULES.items():
        for rule_tuple in rules:
            for action in ACTIONS:
                cases.append((role_name, rule_tuple, action))
    return cases


def _ids_for(cases):
    return [f"{role}-{rule[0]}-{action}" for role, rule, action in cases]


ALL_CASES = _all_cases()
NON_CREATE_CASES = [c for c in ALL_CASES if c[2] != "create"]

ALL_IDS = _ids_for(ALL_CASES)
NON_CREATE_IDS = _ids_for(NON_CREATE_CASES)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_for_role(admin_user, manager_user, developer_user, viewer_user):
    return {
        "admin": admin_user,
        "manager": manager_user,
        "developer": developer_user,
        "viewer": viewer_user,
    }


@pytest.fixture
def stranger_user(roles):
    """
    A user with NO roles assigned. Used purely as an "other owner" —
    its pk must differ from the user under test, and it has no AccessRules
    itself so it can't accidentally satisfy has_any_access/check_access.
    """
    return User.objects.create_user(
        email="stranger@example.com",
        password="testpass123",
        first_name="Stranger",
        last_name="User",
    )


# ---------------------------------------------------------------------------
# has_any_access — endpoint-level gate (list/create)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role_name,rule_tuple,action", ALL_CASES, ids=ALL_IDS)
def test_has_any_access_matches_seed(user_for_role, role_name, rule_tuple, action):
    flags = _unpack(rule_tuple)
    user = user_for_role[role_name]
    expected = _expected_has_any(flags, action)

    assert has_any_access(user, flags["resource"], action) == expected


def test_has_any_access_user_without_roles_is_denied(stranger_user):
    """A user with zero UserRole rows must be denied everything."""
    for resource in ["task", "project", "user", "role", "access_rule"]:
        for action in ACTIONS:
            assert has_any_access(stranger_user, resource, action) is False


def test_has_any_access_inactive_user_is_denied(user_for_role):
    user = user_for_role["admin"]
    user.is_active = False
    user.save(update_fields=["is_active"])

    assert has_any_access(user, "task", "read") is False


# ---------------------------------------------------------------------------
# check_access — object-level check (detail views)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role_name,rule_tuple,action", NON_CREATE_CASES, ids=NON_CREATE_IDS)
def test_check_access_own_object(user_for_role, role_name, rule_tuple, action):
    """
    Object owned BY THE USER: expected = can_{action}_all OR can_{action}.
    """
    flags = _unpack(rule_tuple)
    user = user_for_role[role_name]
    expected = flags["all"][action] or flags["own"][action]

    assert check_access(user, flags["resource"], action, obj_owner_id=user.pk) == expected


@pytest.mark.parametrize("role_name,rule_tuple,action", NON_CREATE_CASES, ids=NON_CREATE_IDS)
def test_check_access_others_object(user_for_role, stranger_user, role_name, rule_tuple, action):
    """
    Object owned by SOMEONE ELSE: the "own" flag never applies —
    expected = can_{action}_all only.
    """
    flags = _unpack(rule_tuple)
    user = user_for_role[role_name]
    expected = flags["all"][action]

    assert check_access(user, flags["resource"], action, obj_owner_id=stranger_user.pk) == expected


@pytest.mark.parametrize("role_name,rule_tuple,action", NON_CREATE_CASES, ids=NON_CREATE_IDS)
def test_check_access_no_owner_given_requires_all_flag(user_for_role, role_name, rule_tuple, action):
    """
    obj_owner_id=None: own-object branch can never trigger —
    expected = can_{action}_all only (mirrors "others_object" case).
    """
    flags = _unpack(rule_tuple)
    user = user_for_role[role_name]
    expected = flags["all"][action]

    assert check_access(user, flags["resource"], action, obj_owner_id=None) == expected


# ---------------------------------------------------------------------------
# get_accessible_queryset — row-level filtering for list endpoints
# ---------------------------------------------------------------------------

@pytest.fixture
def task_pair(developer_user, viewer_user):
    """Two tasks owned by two different users (both with roles assigned)."""
    own = Task.objects.create(title="developer's task", owner=developer_user)
    other = Task.objects.create(title="viewer's task", owner=viewer_user)
    return own, other


@pytest.mark.parametrize("role_name", list(ACCESS_RULES.keys()))
def test_get_accessible_queryset_tasks(user_for_role, task_pair, role_name):
    user = user_for_role[role_name]
    own, other = task_pair

    rule_tuple = next(r for r in ACCESS_RULES[role_name] if r[0] == "task")
    flags = _unpack(rule_tuple)

    qs = get_accessible_queryset(user, "task", "read", Task.objects.all())
    ids = set(qs.values_list("id", flat=True))

    if flags["all"]["read"]:
        assert ids == {own.id, other.id}
    elif flags["own"]["read"]:
        expected = {t.id for t in (own, other) if t.owner_id == user.pk}
        assert ids == expected
    else:
        assert ids == set()


def test_get_accessible_queryset_no_roles_returns_none(stranger_user, task_pair):
    qs = get_accessible_queryset(stranger_user, "task", "read", Task.objects.all())
    assert qs.count() == 0


def test_get_accessible_queryset_inactive_user_returns_none(user_for_role, task_pair):
    user = user_for_role["admin"]  # has can_read_all on task
    user.is_active = False
    user.save(update_fields=["is_active"])

    qs = get_accessible_queryset(user, "task", "read", Task.objects.all())
    assert qs.count() == 0
