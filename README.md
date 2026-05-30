# TaskTracker

API backend for task/project management with custom JWT authentication and ownership-aware RBAC.

**Phase 1 (current):** auth, RBAC, mock task/project endpoints.  
**Phase 2:** real models, tests, Swagger, Docker deploy.

## Stack

- Python 3.12, Django 5, DRF, SimpleJWT
- PostgreSQL 16
- Config via `.env` (`python-decouple`)

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # edit SECRET_KEY and DB_* as needed
```

Requires **Python 3.12** (see `.python-version`). Use `pyenv local` or your tool of choice if needed.

Create the database (PostgreSQL must be running), then:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API base: `http://localhost:8000/api/`  
Admin: `http://localhost:8000/admin/`

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
