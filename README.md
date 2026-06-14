# TaskTracker

![Tests](https://github.com/LilacRapture/tasktracker/actions/workflows/tests.yml/badge.svg)
[![codecov](https://codecov.io/github/LilacRapture/tasktracker/graph/badge.svg?token=S5JBJF7PNE)](https://codecov.io/github/LilacRapture/tasktracker)

API backend for task/project management with custom JWT authentication and ownership-aware RBAC.

**Phase 1:** complete — custom auth, RBAC, user API, mock tasks/projects.  
**Phase 2 (next):** real models, tests, Swagger, Docker deploy.

## Stack

- Python 3.12, Django 5, DRF, SimpleJWT
- PostgreSQL 16
- Config via `.env` (`python-decouple`)

## Local setup

Requires **Python 3.12** (see `.python-version` and `pyproject.toml`). Use 3.12 explicitly — **not 3.13 or 3.14** (Django admin form issues on newer versions).

```bash
python3.12 -m venv .venv    # or: pyenv install 3.12 && pyenv local 3.12
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python --version            # should print 3.12.x
pip install -r requirements.txt
cp .env.example .env        # edit SECRET_KEY and DB_* as needed
```

If you previously used another Python version, delete `.venv` and recreate it with 3.12.

Create the database (PostgreSQL must be running), then:

```bash
python manage.py migrate
python manage.py seed_roles
python manage.py createsuperuser
python manage.py runserver
```

API base: `http://localhost:8000/api/`  
Admin: `http://localhost:8000/admin/`  
API docs (Swagger): `http://localhost:8000/api/docs/`

## Documentation

| File | Purpose |
|------|---------|
| [AGENTS.md](AGENTS.md) | AI agent + project conventions |
| [.cursor/rules/project.mdc](.cursor/rules/project.mdc) | Cursor IDE rules (summary; AGENTS.md is full spec) |
| [docs/architecture.md](docs/architecture.md) | System overview |
| [docs/rbac-schema.md](docs/rbac-schema.md) | **Canonical RBAC spec** |
| [docs/api.md](docs/api.md) | HTTP endpoint reference |
| [docs/decisions.md](docs/decisions.md) | Architecture decision records |

## Docker

`docker-compose.yml` is reserved for Phase 2. A `Dockerfile` is not included yet — use local setup above for now.
