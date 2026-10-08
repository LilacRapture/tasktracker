# TaskTracker

![Tests](https://github.com/LilacRapture/tasktracker/actions/workflows/tests.yml/badge.svg)
[![codecov](https://codecov.io/github/LilacRapture/tasktracker/graph/badge.svg?token=S5JBJF7PNE)](https://codecov.io/github/LilacRapture/tasktracker)

API backend for task/project management with custom JWT authentication, ownership-aware RBAC, and realtime task events over WebSocket.

Project status: see [AGENTS.md](AGENTS.md#project-status).

## Stack

- Python 3.12, Django 5, DRF, SimpleJWT
- PostgreSQL 16, Redis 7
- Django Channels + daphne (WebSocket), gunicorn (HTTP), nginx (reverse proxy)
- Config via `.env` (`python-decouple`)

## Quick start (Docker)

Requires Docker and Docker Compose.

```bash
cp .env.example .env   # edit SECRET_KEY and DB_* as needed
docker-compose up --build
```

This builds the image and starts PostgreSQL, Redis, the HTTP and WebSocket
backends, and nginx. On start the backend waits for PostgreSQL, applies
migrations, seeds RBAC roles, and collects static files.

Everything is served through nginx on port 8000:

- API: `http://localhost:8000/api/`
- Admin: `http://localhost:8000/admin/`
- API docs (Swagger): `http://localhost:8000/api/docs/`
- WebSocket: `ws://localhost:8000/ws/tasktracker/` (see [docs/realtime.md](docs/realtime.md))

Create an admin user for `/admin/`:

```bash
docker-compose exec web python manage.py createsuperuser
```

## Local development (without Docker)

Requires **Python 3.12** (see `.python-version` and `pyproject.toml`). Use 3.12 explicitly — **not 3.13 or 3.14** (Django admin form issues on newer versions).

```bash
python3.12 -m venv .venv    # or: pyenv install 3.12 && pyenv local 3.12
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python --version            # should print 3.12.x
pip install -r requirements.txt
cp .env.example .env        # edit SECRET_KEY and DB_* as needed
```

If you previously used another Python version, delete `.venv` and recreate it with 3.12.

PostgreSQL and Redis must be running. Create the database, then:

```bash
python manage.py migrate
python manage.py seed_roles
python manage.py createsuperuser
python manage.py runserver
```

API base: `http://localhost:8000/api/`  
Admin: `http://localhost:8000/admin/`  
API docs (Swagger): `http://localhost:8000/api/docs/`

`runserver` serves HTTP only. For WebSocket, run the ASGI server in a second terminal:

```bash
daphne -p 8001 config.asgi:application
```

and connect to `ws://localhost:8001/ws/tasktracker/`.

## Tests

PostgreSQL and Redis must be running (same as local development).

```bash
pytest
```

## Documentation

| File | Purpose |
|------|---------|
| [AGENTS.md](AGENTS.md) | AI agent + project conventions, project status |
| [docs/architecture.md](docs/architecture.md) | System overview |
| [docs/rbac-schema.md](docs/rbac-schema.md) | **Canonical RBAC spec** |
| [docs/api.md](docs/api.md) | HTTP endpoint reference |
| [docs/realtime.md](docs/realtime.md) | WebSocket/realtime spec |
| [docs/decisions.md](docs/decisions.md) | Architecture decision records |