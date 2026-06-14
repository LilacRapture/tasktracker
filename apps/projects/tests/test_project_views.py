import pytest

from apps.projects.models import Project

pytestmark = pytest.mark.django_db

PROJECTS_URL = "/api/projects/"


def project_detail_url(pk: int) -> str:
    return f"/api/projects/{pk}/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def developer_project(developer_user):
    return Project.objects.create(name="Developer's project", owner=developer_user)


@pytest.fixture
def viewer_project(viewer_user):
    return Project.objects.create(name="Viewer's project", owner=viewer_user)


# ---------------------------------------------------------------------------
# List — GET /api/projects/
# ---------------------------------------------------------------------------

def test_admin_sees_all_projects(auth_client, admin_user, developer_project, viewer_project):
    client = auth_client(admin_user)
    response = client.get(PROJECTS_URL)

    assert response.status_code == 200
    names = {p["name"] for p in response.json()["results"]}
    assert names == {"Developer's project", "Viewer's project"}


def test_developer_sees_all_projects_read_all(auth_client, developer_user, developer_project, viewer_project):
    client = auth_client(developer_user)
    response = client.get(PROJECTS_URL)

    assert response.status_code == 200
    names = {p["name"] for p in response.json()["results"]}
    assert names == {"Developer's project", "Viewer's project"}


def test_viewer_sees_all_projects_read_all(auth_client, viewer_user, developer_project, viewer_project):
    client = auth_client(viewer_user)
    response = client.get(PROJECTS_URL)

    assert response.status_code == 200
    names = {p["name"] for p in response.json()["results"]}
    assert names == {"Developer's project", "Viewer's project"}


def test_project_list_is_paginated(auth_client, admin_user, developer_project, viewer_project):
    client = auth_client(admin_user)
    response = client.get(PROJECTS_URL)

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) >= {"count", "next", "previous", "results"}
    assert data["count"] == 2


# ---------------------------------------------------------------------------
# Create — POST /api/projects/
# ---------------------------------------------------------------------------

def test_developer_can_create_project(auth_client, developer_user):
    client = auth_client(developer_user)
    response = client.post(PROJECTS_URL, {"name": "New project"})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New project"
    assert data["owner"] == developer_user.id


def test_viewer_cannot_create_project(auth_client, viewer_user):
    client = auth_client(viewer_user)
    response = client.post(PROJECTS_URL, {"name": "Should fail"})

    assert response.status_code == 403
    assert not Project.objects.filter(name="Should fail").exists()


def test_create_owner_is_set_from_request_user_not_body(auth_client, developer_user, viewer_user):
    client = auth_client(developer_user)
    response = client.post(PROJECTS_URL, {"name": "Sneaky project", "owner": viewer_user.id})

    assert response.status_code == 201
    assert response.json()["owner"] == developer_user.id


# ---------------------------------------------------------------------------
# Detail GET
# ---------------------------------------------------------------------------

def test_developer_can_read_others_project_via_read_all(auth_client, developer_user, viewer_project):
    client = auth_client(developer_user)
    response = client.get(project_detail_url(viewer_project.id))

    assert response.status_code == 200
    assert response.json()["name"] == "Viewer's project"


def test_detail_nonexistent_project_returns_404(auth_client, developer_user):
    client = auth_client(developer_user)
    response = client.get(project_detail_url(999999))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update — PATCH /api/projects/{id}/
# ---------------------------------------------------------------------------

def test_developer_can_update_own_project(auth_client, developer_user, developer_project):
    client = auth_client(developer_user)
    response = client.patch(project_detail_url(developer_project.id), {"status": "active"})

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_developer_cannot_update_others_project(auth_client, developer_user, viewer_project):
    """developer has can_update=True (own) but can_update_all=False."""
    client = auth_client(developer_user)
    response = client.patch(project_detail_url(viewer_project.id), {"status": "active"})

    assert response.status_code == 403

    viewer_project.refresh_from_db()
    assert viewer_project.status == "planned"


def test_manager_can_update_any_project(auth_client, manager_user, developer_project):
    client = auth_client(manager_user)
    response = client.patch(project_detail_url(developer_project.id), {"status": "completed"})

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# Delete — DELETE /api/projects/{id}/
# ---------------------------------------------------------------------------

def test_developer_cannot_delete_own_project(auth_client, developer_user, developer_project):
    """developer has can_delete=False AND can_delete_all=False on project — never allowed."""
    client = auth_client(developer_user)
    response = client.delete(project_detail_url(developer_project.id))

    assert response.status_code == 403
    assert Project.objects.filter(pk=developer_project.id).exists()


def test_admin_can_delete_any_project(auth_client, admin_user, viewer_project):
    client = auth_client(admin_user)
    response = client.delete(project_detail_url(viewer_project.id))

    assert response.status_code == 204
    assert not Project.objects.filter(pk=viewer_project.id).exists()


def test_manager_can_delete_any_project(auth_client, manager_user, viewer_project):
    client = auth_client(manager_user)
    response = client.delete(project_detail_url(viewer_project.id))

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Filtering & search — GET /api/projects/
# ---------------------------------------------------------------------------

@pytest.fixture
def projects_for_filtering(developer_user):
    return [
        Project.objects.create(name="Alpha", status="active", owner=developer_user),
        Project.objects.create(name="Beta", status="completed", owner=developer_user),
        Project.objects.create(name="Gamma project", status="planned", owner=developer_user),
    ]


def test_filter_projects_by_status(auth_client, admin_user, projects_for_filtering):
    client = auth_client(admin_user)
    response = client.get(PROJECTS_URL, {"status": "completed"})

    assert response.status_code == 200
    names = {p["name"] for p in response.json()["results"]}
    assert names == {"Beta"}


def test_search_projects_by_name(auth_client, admin_user, projects_for_filtering):
    client = auth_client(admin_user)
    response = client.get(PROJECTS_URL, {"search": "project"})

    assert response.status_code == 200
    names = {p["name"] for p in response.json()["results"]}
    assert names == {"Gamma project"}


def test_order_projects_by_name(auth_client, admin_user, projects_for_filtering):
    client = auth_client(admin_user)
    response = client.get(PROJECTS_URL, {"ordering": "name"})

    assert response.status_code == 200
    names = [p["name"] for p in response.json()["results"]]
    assert names == sorted(names)    
    