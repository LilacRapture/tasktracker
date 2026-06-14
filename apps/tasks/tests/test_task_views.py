import pytest

from apps.tasks.models import Task

pytestmark = pytest.mark.django_db

TASKS_URL = "/api/tasks/"


def task_detail_url(pk: int) -> str:
    return f"/api/tasks/{pk}/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def developer_task(developer_user):
    return Task.objects.create(title="Developer's task", owner=developer_user)


@pytest.fixture
def viewer_task(viewer_user):
    return Task.objects.create(title="Viewer's task", owner=viewer_user)


# ---------------------------------------------------------------------------
# List — GET /api/tasks/
# ---------------------------------------------------------------------------

def test_admin_sees_all_tasks(auth_client, admin_user, developer_task, viewer_task):
    client = auth_client(admin_user)
    response = client.get(TASKS_URL)

    assert response.status_code == 200
    titles = {t["title"] for t in response.json()["results"]}
    assert titles == {"Developer's task", "Viewer's task"}


def test_developer_sees_all_tasks_read_all(auth_client, developer_user, developer_task, viewer_task):
    """developer has can_read_all=True on task — sees everyone's tasks."""
    client = auth_client(developer_user)
    response = client.get(TASKS_URL)

    assert response.status_code == 200
    titles = {t["title"] for t in response.json()["results"]}
    assert titles == {"Developer's task", "Viewer's task"}


def test_viewer_sees_all_tasks_read_all(auth_client, viewer_user, developer_task, viewer_task):
    """viewer has can_read_all=True on task too."""
    client = auth_client(viewer_user)
    response = client.get(TASKS_URL)

    assert response.status_code == 200
    titles = {t["title"] for t in response.json()["results"]}
    assert titles == {"Developer's task", "Viewer's task"}


def test_list_requires_authentication(api_client):
    response = api_client.get(TASKS_URL)
    assert response.status_code == 401


def test_task_list_is_paginated(auth_client, admin_user, developer_task, viewer_task):
    client = auth_client(admin_user)
    response = client.get(TASKS_URL)

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) >= {"count", "next", "previous", "results"}
    assert data["count"] == 2


# ---------------------------------------------------------------------------
# Create — POST /api/tasks/
# ---------------------------------------------------------------------------

def test_developer_can_create_task(auth_client, developer_user):
    client = auth_client(developer_user)
    response = client.post(TASKS_URL, {"title": "New task", "status": "todo"})

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New task"
    assert data["owner"]["email"] == developer_user.email
    assert data["project"] is None


def test_manager_can_create_task(auth_client, manager_user):
    client = auth_client(manager_user)
    response = client.post(TASKS_URL, {"title": "Manager task"})
    assert response.status_code == 201


def test_viewer_cannot_create_task(auth_client, viewer_user):
    client = auth_client(viewer_user)
    response = client.post(TASKS_URL, {"title": "Should fail"})

    assert response.status_code == 403
    assert not Task.objects.filter(title="Should fail").exists()


def test_create_owner_is_set_from_request_user_not_body(auth_client, developer_user, viewer_user):
    """owner must always be the requesting user, regardless of what's posted."""
    client = auth_client(developer_user)
    response = client.post(TASKS_URL, {"title": "Sneaky task", "owner": viewer_user.id})

    assert response.status_code == 201
    data = response.json()
    assert data["owner"]["email"] == developer_user.email


# ---------------------------------------------------------------------------
# Detail GET — own vs others'
# ---------------------------------------------------------------------------

def test_developer_can_read_own_task_detail(auth_client, developer_user, developer_task):
    client = auth_client(developer_user)
    response = client.get(task_detail_url(developer_task.id))

    assert response.status_code == 200
    assert response.json()["title"] == "Developer's task"


def test_developer_can_read_others_task_detail_via_read_all(auth_client, developer_user, viewer_task):
    """developer has can_read_all on task, so can read viewer's task too."""
    client = auth_client(developer_user)
    response = client.get(task_detail_url(viewer_task.id))

    assert response.status_code == 200
    assert response.json()["title"] == "Viewer's task"


def test_detail_nonexistent_task_returns_404(auth_client, developer_user):
    client = auth_client(developer_user)
    response = client.get(task_detail_url(999999))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update — PATCH /api/tasks/{id}/
# ---------------------------------------------------------------------------

def test_developer_can_update_own_task(auth_client, developer_user, developer_task):
    client = auth_client(developer_user)
    response = client.patch(task_detail_url(developer_task.id), {"status": "done"})

    assert response.status_code == 200
    assert response.json()["status"] == "done"

    developer_task.refresh_from_db()
    assert developer_task.status == "done"


def test_developer_cannot_update_others_task(auth_client, developer_user, viewer_task):
    """developer has can_update=True (own) but can_update_all=False."""
    client = auth_client(developer_user)
    response = client.patch(task_detail_url(viewer_task.id), {"status": "done"})

    assert response.status_code == 403

    viewer_task.refresh_from_db()
    assert viewer_task.status == "todo"


def test_manager_can_update_any_task(auth_client, manager_user, developer_task):
    """manager has can_update_all=True on task."""
    client = auth_client(manager_user)
    response = client.patch(task_detail_url(developer_task.id), {"status": "in_progress"})

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_viewer_cannot_update_any_task(auth_client, viewer_user, viewer_task):
    """viewer has no update flags at all — denied at has_permission level."""
    client = auth_client(viewer_user)
    response = client.patch(task_detail_url(viewer_task.id), {"status": "done"})

    assert response.status_code == 403


def test_update_does_not_change_owner(auth_client, developer_user, developer_task, viewer_user):
    client = auth_client(developer_user)
    response = client.patch(
        task_detail_url(developer_task.id),
        {"status": "done", "owner": viewer_user.id},
    )

    assert response.status_code == 200
    developer_task.refresh_from_db()
    assert developer_task.owner_id == developer_user.id


# ---------------------------------------------------------------------------
# Delete — DELETE /api/tasks/{id}/
# ---------------------------------------------------------------------------

def test_developer_can_delete_own_task(auth_client, developer_user, developer_task):
    client = auth_client(developer_user)
    response = client.delete(task_detail_url(developer_task.id))

    assert response.status_code == 204
    assert not Task.objects.filter(pk=developer_task.id).exists()


def test_developer_cannot_delete_others_task(auth_client, developer_user, viewer_task):
    """developer has can_delete_all=False — cannot delete viewer's task."""
    client = auth_client(developer_user)
    response = client.delete(task_detail_url(viewer_task.id))

    assert response.status_code == 403
    assert Task.objects.filter(pk=viewer_task.id).exists()


def test_admin_can_delete_any_task(auth_client, admin_user, viewer_task):
    client = auth_client(admin_user)
    response = client.delete(task_detail_url(viewer_task.id))

    assert response.status_code == 204
    assert not Task.objects.filter(pk=viewer_task.id).exists()


def test_viewer_cannot_delete_any_task(auth_client, viewer_user, viewer_task):
    client = auth_client(viewer_user)
    response = client.delete(task_detail_url(viewer_task.id))

    assert response.status_code == 403
    assert Task.objects.filter(pk=viewer_task.id).exists()
    