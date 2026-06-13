import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.rbac.models import Role, UserRole

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def roles(db):
    """
    Create the four seed roles with their AccessRules,
    mirroring apps/rbac/management/commands/seed_roles.py.
    """
    from django.core.management import call_command
    call_command("seed_roles")
    return {r.name: r for r in Role.objects.all()}


def _make_user(email, roles_dict, role_names):
    user = User.objects.create_user(
        email=email,
        password="testpass123",
        first_name="Test",
        last_name="User",
    )
    for name in role_names:
        UserRole.objects.create(user=user, role=roles_dict[name])
    return user


@pytest.fixture
def admin_user(roles):
    return _make_user("admin@example.com", roles, ["admin"])


@pytest.fixture
def manager_user(roles):
    return _make_user("manager@example.com", roles, ["manager"])


@pytest.fixture
def developer_user(roles):
    return _make_user("developer@example.com", roles, ["developer"])


@pytest.fixture
def viewer_user(roles):
    return _make_user("viewer@example.com", roles, ["viewer"])


@pytest.fixture
def auth_client(api_client):
    """Returns a function: auth_client(user) -> APIClient with Bearer token set."""
    def _authenticate(user):
        from rest_framework_simplejwt.tokens import RefreshToken
        token = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return api_client
    return _authenticate
    