import pytest

from apps.rbac.models import UserRole

pytestmark = pytest.mark.django_db

CAPABILITIES_URL = "/api/users/me/capabilities/"


def test_requires_authentication(api_client):
    response = api_client.get(CAPABILITIES_URL)
    assert response.status_code == 401


def test_developer_capabilities_match_seed_data(auth_client, developer_user):
    """Cross-check against docs/rbac-schema.md's developer row."""
    client = auth_client(developer_user)
    response = client.get(CAPABILITIES_URL)

    assert response.status_code == 200
    data = response.json()

    assert data["roles"] == ["developer"]
    assert data["capabilities"]["task"] == {
        "can_read": True,
        "can_read_all": True,
        "can_create": True,
        "can_update": True,
        "can_update_all": False,
        "can_delete": True,
        "can_delete_all": False,
    }
    assert data["capabilities"]["user"] == {
        "can_read": False,
        "can_read_all": False,
        "can_create": False,
        "can_update": False,
        "can_update_all": False,
        "can_delete": False,
        "can_delete_all": False,
    }


def test_user_with_no_roles_gets_empty_roles_and_all_false_capabilities(auth_client, stranger_user):
    client = auth_client(stranger_user)
    response = client.get(CAPABILITIES_URL)

    assert response.status_code == 200
    data = response.json()

    assert data["roles"] == []
    for resource_flags in data["capabilities"].values():
        assert all(flag is False for flag in resource_flags.values())


def test_user_with_multiple_roles_gets_merged_capabilities(auth_client, developer_user, roles):
    """
    developer alone has no 'user' resource access at all; adding admin
    (which has full access to everything) must OR that in — merged
    capabilities.user.can_read_all should flip to True.
    """
    UserRole.objects.create(user=developer_user, role=roles["admin"])

    client = auth_client(developer_user)
    response = client.get(CAPABILITIES_URL)

    data = response.json()
    assert set(data["roles"]) == {"developer", "admin"}
    assert data["capabilities"]["user"]["can_read_all"] is True
