import pytest

from apps.rbac.models import AccessRule, Role, UserRole

pytestmark = pytest.mark.django_db

ROLES_URL = "/api/rbac/roles/"
USERS_URL = "/api/users/"


def role_detail_url(pk: int) -> str:
    return f"/api/rbac/roles/{pk}/"


def rules_url(role_id: int) -> str:
    return f"/api/rbac/roles/{role_id}/rules/"


def rule_detail_url(role_id: int, resource: str) -> str:
    return f"/api/rbac/roles/{role_id}/rules/{resource}/"


def user_roles_url(user_id: int) -> str:
    return f"/api/users/{user_id}/roles/"


def user_role_detail_url(user_id: int, role_id: int) -> str:
    return f"/api/users/{user_id}/roles/{role_id}/"


# ---------------------------------------------------------------------------
# Roles — GET /api/rbac/roles/
# ---------------------------------------------------------------------------

def test_admin_can_list_roles(auth_client, admin_user, roles):
    client = auth_client(admin_user)
    response = client.get(ROLES_URL)

    assert response.status_code == 200
    names = {r["name"] for r in response.json()}
    assert {"admin", "manager", "developer", "viewer"} == names


def test_manager_cannot_list_roles(auth_client, manager_user, roles):
    """manager has all False on 'role' resource."""
    client = auth_client(manager_user)
    response = client.get(ROLES_URL)
    assert response.status_code == 403


def test_developer_cannot_list_roles(auth_client, developer_user, roles):
    client = auth_client(developer_user)
    response = client.get(ROLES_URL)
    assert response.status_code == 403


def test_role_list_response_includes_access_rules(auth_client, admin_user, roles):
    client = auth_client(admin_user)
    response = client.get(ROLES_URL)

    role_data = next(r for r in response.json() if r["name"] == "admin")
    assert "access_rules" in role_data
    assert len(role_data["access_rules"]) > 0


# ---------------------------------------------------------------------------
# Roles — POST /api/rbac/roles/
# ---------------------------------------------------------------------------

def test_admin_can_create_role(auth_client, admin_user, roles):
    client = auth_client(admin_user)
    response = client.post(ROLES_URL, {
        "name": "auditor",
        "description": "Read-only audit role",
    })

    assert response.status_code == 201
    assert response.json()["name"] == "auditor"
    assert Role.objects.filter(name="auditor").exists()


def test_manager_cannot_create_role(auth_client, manager_user, roles):
    client = auth_client(manager_user)
    response = client.post(ROLES_URL, {"name": "sneaky_role"})

    assert response.status_code == 403
    assert not Role.objects.filter(name="sneaky_role").exists()


def test_create_role_requires_unique_name(auth_client, admin_user, roles):
    client = auth_client(admin_user)
    response = client.post(ROLES_URL, {"name": "admin"})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Roles — GET /api/rbac/roles/{id}/
# ---------------------------------------------------------------------------

def test_admin_can_get_role_detail(auth_client, admin_user, roles):
    role = roles["developer"]
    client = auth_client(admin_user)
    response = client.get(role_detail_url(role.id))

    assert response.status_code == 200
    assert response.json()["name"] == "developer"


def test_role_detail_nonexistent_returns_404(auth_client, admin_user, roles):
    client = auth_client(admin_user)
    response = client.get(role_detail_url(999999))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Roles — PATCH /api/rbac/roles/{id}/
# ---------------------------------------------------------------------------

def test_admin_can_update_role(auth_client, admin_user, roles):
    role = roles["viewer"]
    client = auth_client(admin_user)
    response = client.patch(role_detail_url(role.id), {"description": "Updated description"})

    assert response.status_code == 200
    role.refresh_from_db()
    assert role.description == "Updated description"


def test_manager_cannot_update_role(auth_client, manager_user, roles):
    role = roles["viewer"]
    client = auth_client(manager_user)
    response = client.patch(role_detail_url(role.id), {"description": "Hacked"})

    assert response.status_code == 403
    role.refresh_from_db()
    assert role.description != "Hacked"


# ---------------------------------------------------------------------------
# Roles — DELETE /api/rbac/roles/{id}/
# ---------------------------------------------------------------------------

def test_admin_can_delete_role(auth_client, admin_user, roles):
    role = Role.objects.create(name="temp_role", description="To be deleted")
    client = auth_client(admin_user)
    response = client.delete(role_detail_url(role.id))

    assert response.status_code == 204
    assert not Role.objects.filter(pk=role.id).exists()


def test_manager_cannot_delete_role(auth_client, manager_user, roles):
    role = roles["viewer"]
    client = auth_client(manager_user)
    response = client.delete(role_detail_url(role.id))

    assert response.status_code == 403
    assert Role.objects.filter(pk=role.id).exists()


# ---------------------------------------------------------------------------
# Access Rules — GET /api/rbac/roles/{id}/rules/
# ---------------------------------------------------------------------------

def test_admin_can_list_access_rules_for_role(auth_client, admin_user, roles):
    role = roles["developer"]
    client = auth_client(admin_user)
    response = client.get(rules_url(role.id))

    assert response.status_code == 200
    resources = {r["resource"] for r in response.json()}
    assert "task" in resources
    assert "project" in resources


def test_rules_for_nonexistent_role_returns_404(auth_client, admin_user, roles):
    client = auth_client(admin_user)
    response = client.get(rules_url(999999))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Access Rules — POST /api/rbac/roles/{id}/rules/
# ---------------------------------------------------------------------------

def test_admin_can_create_access_rule(auth_client, admin_user, roles):
    role = Role.objects.create(name="custom_role")
    client = auth_client(admin_user)
    response = client.post(rules_url(role.id), {
        "resource": "task",
        "can_read": True,
        "can_read_all": False,
        "can_create": False,
        "can_update": False,
        "can_update_all": False,
        "can_delete": False,
        "can_delete_all": False,
    })

    assert response.status_code == 201
    assert AccessRule.objects.filter(role=role, resource="task").exists()


def test_cannot_create_duplicate_access_rule(auth_client, admin_user, roles):
    """(role, resource) unique_together must be enforced by the view."""
    role = roles["developer"]
    client = auth_client(admin_user)
    response = client.post(rules_url(role.id), {
        "resource": "task",  # developer already has a task rule from seed
        "can_read": True,
    })

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Access Rules — PATCH /api/rbac/roles/{id}/rules/{resource}/
# ---------------------------------------------------------------------------

def test_admin_can_update_access_rule(auth_client, admin_user, roles):
    role = roles["viewer"]
    client = auth_client(admin_user)
    response = client.patch(rule_detail_url(role.id, "task"), {"can_create": True})

    assert response.status_code == 200
    assert response.json()["can_create"] is True

    rule = AccessRule.objects.get(role=role, resource="task")
    assert rule.can_create is True


def test_update_nonexistent_rule_returns_404(auth_client, admin_user, roles):
    role = Role.objects.create(name="empty_role")  # no AccessRule rows at all
    client = auth_client(admin_user)
    response = client.patch(rule_detail_url(role.id, "task"), {"can_read": True})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Access Rules — DELETE /api/rbac/roles/{id}/rules/{resource}/
# ---------------------------------------------------------------------------

def test_admin_can_delete_access_rule(auth_client, admin_user, roles):
    role = Role.objects.create(name="temp_role2")
    rule = AccessRule.objects.create(role=role, resource="task", can_read=True)

    client = auth_client(admin_user)
    response = client.delete(rule_detail_url(role.id, "task"))

    assert response.status_code == 204
    assert not AccessRule.objects.filter(pk=rule.id).exists()


def test_delete_nonexistent_rule_returns_404(auth_client, admin_user, roles):
    role = Role.objects.create(name="empty_role2")
    client = auth_client(admin_user)
    response = client.delete(rule_detail_url(role.id, "task"))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# User Role Assignment — GET /api/users/{id}/roles/
# ---------------------------------------------------------------------------

def test_admin_can_list_user_roles(auth_client, admin_user, developer_user, roles):
    client = auth_client(admin_user)
    response = client.get(user_roles_url(developer_user.id))

    assert response.status_code == 200
    role_names = {r["role_name"] for r in response.json()}
    assert "developer" in role_names


def test_manager_cannot_list_user_roles(auth_client, manager_user, developer_user, roles):
    """manager has all False on 'role' resource."""
    client = auth_client(manager_user)
    response = client.get(user_roles_url(developer_user.id))
    assert response.status_code == 403


def test_list_roles_for_nonexistent_user_returns_404(auth_client, admin_user, roles):
    client = auth_client(admin_user)
    response = client.get(user_roles_url(999999))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# User Role Assignment — POST /api/users/{id}/roles/
# ---------------------------------------------------------------------------

def test_admin_can_assign_role_to_user(auth_client, admin_user, viewer_user, roles):
    developer_role = roles["developer"]
    client = auth_client(admin_user)
    response = client.post(
        user_roles_url(viewer_user.id),
        {"role_id": developer_role.id},
    )

    assert response.status_code == 201
    assert UserRole.objects.filter(user=viewer_user, role=developer_role).exists()


def test_assigned_by_is_set_to_requesting_user(auth_client, admin_user, viewer_user, roles):
    developer_role = roles["developer"]
    client = auth_client(admin_user)
    client.post(user_roles_url(viewer_user.id), {"role_id": developer_role.id})

    user_role = UserRole.objects.get(user=viewer_user, role=developer_role)
    assert user_role.assigned_by_id == admin_user.id


def test_cannot_assign_duplicate_role(auth_client, admin_user, developer_user, roles):
    """developer already has developer role from fixture — should fail."""
    developer_role = roles["developer"]
    client = auth_client(admin_user)
    response = client.post(
        user_roles_url(developer_user.id),
        {"role_id": developer_role.id},
    )

    assert response.status_code == 400


def test_cannot_assign_nonexistent_role(auth_client, admin_user, viewer_user, roles):
    client = auth_client(admin_user)
    response = client.post(user_roles_url(viewer_user.id), {"role_id": 999999})
    assert response.status_code == 400


def test_manager_cannot_assign_role(auth_client, manager_user, viewer_user, roles):
    developer_role = roles["developer"]
    client = auth_client(manager_user)
    response = client.post(
        user_roles_url(viewer_user.id),
        {"role_id": developer_role.id},
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# User Role Assignment — DELETE /api/users/{id}/roles/{role_id}/
# ---------------------------------------------------------------------------

def test_admin_can_remove_role_from_user(auth_client, admin_user, developer_user, roles):
    developer_role = roles["developer"]
    client = auth_client(admin_user)
    response = client.delete(user_role_detail_url(developer_user.id, developer_role.id))

    assert response.status_code == 204
    assert not UserRole.objects.filter(user=developer_user, role=developer_role).exists()


def test_remove_nonexistent_user_role_returns_404(auth_client, admin_user, viewer_user, roles):
    developer_role = roles["developer"]  # viewer doesn't have this role
    client = auth_client(admin_user)
    response = client.delete(user_role_detail_url(viewer_user.id, developer_role.id))

    assert response.status_code == 404


def test_manager_cannot_remove_role(auth_client, manager_user, developer_user, roles):
    developer_role = roles["developer"]
    client = auth_client(manager_user)
    response = client.delete(user_role_detail_url(developer_user.id, developer_role.id))

    assert response.status_code == 403
    assert UserRole.objects.filter(user=developer_user, role=developer_role).exists()
    