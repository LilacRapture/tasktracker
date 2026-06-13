import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

pytestmark = pytest.mark.django_db


REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
LOGOUT_URL = "/api/auth/logout/"
REFRESH_URL = "/api/auth/refresh/"


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

def test_register_creates_user_and_returns_tokens(api_client):
    response = api_client.post(REGISTER_URL, {
        "email": "newuser@example.com",
        "password": "StrongPass123!",
        "password_confirm": "StrongPass123!",
        "first_name": "New",
        "last_name": "User",
    })

    assert response.status_code == 201
    data = response.json()

    assert data["user"]["email"] == "newuser@example.com"
    assert "access" in data
    assert "refresh" in data

    assert User.objects.filter(email="newuser@example.com").exists()


def test_register_rejects_mismatched_passwords(api_client):
    response = api_client.post(REGISTER_URL, {
        "email": "newuser2@example.com",
        "password": "StrongPass123!",
        "password_confirm": "DifferentPass123!",
        "first_name": "New",
        "last_name": "User",
    })

    assert response.status_code == 400
    assert "password" in response.json()
    assert not User.objects.filter(email="newuser2@example.com").exists()


def test_register_rejects_duplicate_email(api_client):
    User.objects.create_user(
        email="dupe@example.com",
        password="StrongPass123!",
        first_name="Existing",
        last_name="User",
    )

    response = api_client.post(REGISTER_URL, {
        "email": "dupe@example.com",
        "password": "StrongPass123!",
        "password_confirm": "StrongPass123!",
        "first_name": "New",
        "last_name": "User",
    })

    assert response.status_code == 400


def test_register_rejects_weak_password(api_client):
    response = api_client.post(REGISTER_URL, {
        "email": "weakpass@example.com",
        "password": "123",
        "password_confirm": "123",
        "first_name": "New",
        "last_name": "User",
    })

    assert response.status_code == 400
    assert "password" in response.json()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_with_valid_credentials(api_client):
    User.objects.create_user(
        email="loginuser@example.com",
        password="StrongPass123!",
        first_name="Login",
        last_name="User",
    )

    response = api_client.post(LOGIN_URL, {
        "email": "loginuser@example.com",
        "password": "StrongPass123!",
    })

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "loginuser@example.com"
    assert "access" in data
    assert "refresh" in data


def test_login_with_wrong_password(api_client):
    User.objects.create_user(
        email="loginuser2@example.com",
        password="StrongPass123!",
        first_name="Login",
        last_name="User",
    )

    response = api_client.post(LOGIN_URL, {
        "email": "loginuser2@example.com",
        "password": "WrongPassword!",
    })

    assert response.status_code == 400
    assert "non_field_errors" in response.json()


def test_login_with_nonexistent_email(api_client):
    response = api_client.post(LOGIN_URL, {
        "email": "doesnotexist@example.com",
        "password": "whatever",
    })

    assert response.status_code == 400
    assert "non_field_errors" in response.json()


def test_login_error_message_same_for_missing_user_and_wrong_password(api_client):
    """
    Same error message for 'no such user' and 'wrong password' —
    avoids leaking which emails are registered (see LoginSerializer docstring).
    """
    User.objects.create_user(
        email="realuser@example.com",
        password="StrongPass123!",
        first_name="Real",
        last_name="User",
    )

    wrong_password_resp = api_client.post(LOGIN_URL, {
        "email": "realuser@example.com",
        "password": "WrongPassword!",
    })
    no_user_resp = api_client.post(LOGIN_URL, {
        "email": "nouser@example.com",
        "password": "WrongPassword!",
    })

    assert wrong_password_resp.json()["non_field_errors"] == no_user_resp.json()["non_field_errors"]


def test_login_rejects_soft_deleted_user(api_client):
    user = User.objects.create_user(
        email="deactivated@example.com",
        password="StrongPass123!",
        first_name="Deactivated",
        last_name="User",
    )
    user.soft_delete()

    response = api_client.post(LOGIN_URL, {
        "email": "deactivated@example.com",
        "password": "StrongPass123!",
    })

    assert response.status_code == 400
    assert "non_field_errors" in response.json()


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def test_logout_blacklists_refresh_token(api_client):
    user = User.objects.create_user(
        email="logoutuser@example.com",
        password="StrongPass123!",
        first_name="Logout",
        last_name="User",
    )

    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    response = api_client.post(LOGOUT_URL, {"refresh": str(refresh)})
    assert response.status_code == 200

    # Token should now be blacklisted — refresh should fail
    refresh_response = api_client.post(REFRESH_URL, {"refresh": str(refresh)})
    assert refresh_response.status_code == 401


def test_logout_requires_authentication(api_client):
    response = api_client.post(LOGOUT_URL, {"refresh": "irrelevant"})
    assert response.status_code == 401


def test_logout_rejects_invalid_refresh_token(api_client):
    user = User.objects.create_user(
        email="logoutuser2@example.com",
        password="StrongPass123!",
        first_name="Logout",
        last_name="User",
    )

    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    response = api_client.post(LOGOUT_URL, {"refresh": "not-a-real-token"})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

def test_refresh_returns_new_access_token(api_client):
    user = User.objects.create_user(
        email="refreshuser@example.com",
        password="StrongPass123!",
        first_name="Refresh",
        last_name="User",
    )

    refresh = RefreshToken.for_user(user)

    response = api_client.post(REFRESH_URL, {"refresh": str(refresh)})

    assert response.status_code == 200
    assert "access" in response.json()


def test_refresh_with_invalid_token(api_client):
    response = api_client.post(REFRESH_URL, {"refresh": "not-a-real-token"})
    assert response.status_code == 401
    