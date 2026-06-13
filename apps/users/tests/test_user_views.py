import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

pytestmark = pytest.mark.django_db

ME_URL = "/api/users/me/"
USERS_URL = "/api/users/"


def user_detail_url(pk: int) -> str:
    return f"/api/users/{pk}/"


# ---------------------------------------------------------------------------
# MeView — GET /api/users/me/
# ---------------------------------------------------------------------------

def test_get_own_profile(auth_client, developer_user):
    client = auth_client(developer_user)
    response = client.get(ME_URL)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == developer_user.email
    assert data["full_name"] == developer_user.full_name
    assert "password" not in data


def test_get_own_profile_requires_authentication(api_client):
    response = api_client.get(ME_URL)
    assert response.status_code == 401


def test_any_authenticated_user_can_access_me(auth_client, viewer_user):
    """/me/ has no RBAC resource — IsAuthenticated only."""
    client = auth_client(viewer_user)
    response = client.get(ME_URL)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# MeView — PATCH /api/users/me/
# ---------------------------------------------------------------------------

def test_update_own_profile(auth_client, developer_user):
    client = auth_client(developer_user)
    response = client.patch(ME_URL, {
        "first_name": "Updated",
        "last_name": "Name",
        "middle_name": "M",
    })

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name"
    assert data["middle_name"] == "M"

    developer_user.refresh_from_db()
    assert developer_user.first_name == "Updated"


def test_update_profile_cannot_change_email(auth_client, developer_user):
    original_email = developer_user.email
    client = auth_client(developer_user)

    response = client.patch(ME_URL, {"email": "hacked@example.com"})

    assert response.status_code == 200  # email field is ignored, not an error
    developer_user.refresh_from_db()
    assert developer_user.email == original_email


def test_update_profile_partial(auth_client, developer_user):
    client = auth_client(developer_user)
    response = client.patch(ME_URL, {"first_name": "OnlyFirst"})

    assert response.status_code == 200
    developer_user.refresh_from_db()
    assert developer_user.first_name == "OnlyFirst"
    # last_name unchanged
    assert developer_user.last_name == "User"


# ---------------------------------------------------------------------------
# MeView — DELETE /api/users/me/ (soft delete)
# ---------------------------------------------------------------------------

def test_soft_delete_own_account(auth_client, developer_user):
    client = auth_client(developer_user)
    response = client.delete(ME_URL)

    assert response.status_code == 200
    assert response.json()["detail"] == "Account deactivated successfully."

    developer_user.refresh_from_db()
    assert developer_user.is_active is False


def test_soft_delete_blacklists_provided_refresh_token(auth_client, developer_user):
    refresh = RefreshToken.for_user(developer_user)
    client = auth_client(developer_user)

    response = client.delete(ME_URL, {"refresh": str(refresh)}, format="json")
    assert response.status_code == 200

    # That refresh token should now be unusable
    from rest_framework.test import APIClient
    fresh_client = APIClient()
    refresh_response = fresh_client.post("/api/auth/refresh/", {"refresh": str(refresh)})
    assert refresh_response.status_code == 401


def test_soft_delete_with_invalid_refresh_token_still_succeeds(auth_client, developer_user):
    """Invalid/garbage refresh token must not block account deactivation."""
    client = auth_client(developer_user)
    response = client.delete(ME_URL, {"refresh": "not-a-real-token"}, format="json")

    assert response.status_code == 200
    developer_user.refresh_from_db()
    assert developer_user.is_active is False


def test_soft_deleted_user_cannot_login_again(auth_client, developer_user):
    client = auth_client(developer_user)
    client.delete(ME_URL)

    from rest_framework.test import APIClient
    fresh_client = APIClient()
    response = fresh_client.post("/api/auth/login/", {
        "email": developer_user.email,
        "password": "testpass123",
    })
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# UserListView — GET /api/users/
# ---------------------------------------------------------------------------

def test_admin_can_list_users(auth_client, admin_user, manager_user, developer_user, viewer_user):
    client = auth_client(admin_user)
    response = client.get(USERS_URL)

    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert admin_user.email in emails
    assert developer_user.email in emails


def test_manager_can_list_users(auth_client, manager_user):
    """manager has can_read_all on 'user' resource."""
    client = auth_client(manager_user)
    response = client.get(USERS_URL)
    assert response.status_code == 200


def test_developer_cannot_list_users(auth_client, developer_user):
    """developer has no read flags on 'user' resource."""
    client = auth_client(developer_user)
    response = client.get(USERS_URL)
    assert response.status_code == 403


def test_viewer_cannot_list_users(auth_client, viewer_user):
    client = auth_client(viewer_user)
    response = client.get(USERS_URL)
    assert response.status_code == 403


def test_user_list_excludes_inactive_users(auth_client, admin_user, developer_user):
    developer_user.soft_delete()

    client = auth_client(admin_user)
    response = client.get(USERS_URL)

    emails = {u["email"] for u in response.json()}
    assert developer_user.email not in emails


# ---------------------------------------------------------------------------
# UserDetailView — GET /api/users/{id}/
# ---------------------------------------------------------------------------

def test_admin_can_view_any_user_detail(auth_client, admin_user, developer_user):
    client = auth_client(admin_user)
    response = client.get(user_detail_url(developer_user.id))

    assert response.status_code == 200
    assert response.json()["email"] == developer_user.email


def test_manager_can_view_any_user_detail(auth_client, manager_user, viewer_user):
    client = auth_client(manager_user)
    response = client.get(user_detail_url(viewer_user.id))
    assert response.status_code == 200


def test_developer_cannot_view_other_user_detail(auth_client, developer_user, viewer_user):
    """developer has no 'user' read access at all — even for other profiles."""
    client = auth_client(developer_user)
    response = client.get(user_detail_url(viewer_user.id))
    assert response.status_code == 403


def test_user_detail_nonexistent_id_returns_404(auth_client, admin_user):
    client = auth_client(admin_user)
    response = client.get(user_detail_url(999999))
    assert response.status_code == 404


def test_user_detail_excludes_inactive_users(auth_client, admin_user, developer_user):
    developer_user.soft_delete()

    client = auth_client(admin_user)
    response = client.get(user_detail_url(developer_user.id))
    assert response.status_code == 404
    