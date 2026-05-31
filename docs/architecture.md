# Architecture Overview — TaskTracker

## System Purpose

TaskTracker is an API-only backend that provides:
1. Custom authentication (JWT-based, stateless)
2. Custom RBAC (ownership-aware access rules) with its own DB schema
3. Task and project management as the business domain

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 (pinned; see `.python-version`, `pyproject.toml`) |
| Framework | Django 5 + Django REST Framework |
| Auth tokens | djangorestframework-simplejwt |
| Database | PostgreSQL 16 |
| Config | python-decouple (.env) |
| Containerization | Docker + docker-compose (Phase 2 — not set up yet) |
| API docs | drf-spectacular (Phase 2) |

## Project Layout

```
tasktracker/
├── config/                  # Django project config (settings, root urls)
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── users/               # Custom User model, profile endpoints
│   │   ├── models.py        # User (AbstractBaseUser + PermissionsMixin for admin)
│   │   ├── managers.py      # UserManager
│   │   ├── serializers.py
│   │   ├── views.py         # Profile CRUD, soft delete
│   │   └── urls.py
│   │
│   ├── auth_core/           # Auth flow (register, login, logout, token refresh)
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── tokens.py        # JWT helpers
│   │   └── urls.py
│   │
│   ├── rbac/                # Role-based access control
│   │   ├── models.py        # Role, AccessRule, UserRole
│   │   ├── permissions.py   # RBACPermission + check_access()
│   │   ├── middleware.py    # Optional: attach user roles to request
│   │   ├── views.py         # Admin API: roles, access rules
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   ├── tasks/               # Task business domain
│   │   ├── views.py         # Phase 1: mock. Phase 2: real CRUD
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   └── projects/            # Project business domain
│       ├── views.py
│       ├── serializers.py
│       └── urls.py
│
├── docs/
│   ├── architecture.md      # This file
│   ├── decisions.md         # ADR log
│   ├── rbac-schema.md       # RBAC DB schema (canonical)
│   └── api.md               # Endpoint reference
│
├── AGENTS.md                # AI agent instructions
├── .cursor/rules/project.mdc  # Cursor IDE rules (see AGENTS.md)
├── .python-version          # pyenv / local Python pin (3.12)
├── pyproject.toml           # requires-python pin (3.12.x)
├── .env.example
├── docker-compose.yml       # Phase 2 (Dockerfile not added yet)
└── requirements.txt
```

## Request Lifecycle

```
HTTP Request
    │
    ▼
config/urls.py  ──► routes to app urls.py
    │
    ▼
DRF View
    │
    ├── IsAuthenticated (SimpleJWT validates Bearer token)
    │       └── 401 if token missing/invalid
    │
    ├── RBACPermission (check_access: resource + action, optional owner)
    │       └── 403 if user lacks required access
    │
    └── View logic → Serializer → Response
```

## Authentication Flow

```
POST /api/auth/register/  →  creates User (is_active=True)
POST /api/auth/login/     →  returns {access, refresh} JWT tokens
POST /api/auth/logout/    →  blacklists refresh token
POST /api/auth/refresh/   →  returns new access token

All other endpoints:
  Header: Authorization: Bearer <access_token>
```

Django's session middleware remains enabled for `/admin/` only. API views use JWT, not session cookies.

## RBAC Flow

See `docs/rbac-schema.md` for the full algorithm and seed data.

```
User ──has──► UserRole ──► Role ──has──► AccessRule
                                              │
                              resource: "task"
                              can_read        │ ← read own objects
                              can_read_all    │ ← read any object
                              can_create      │
                              can_update      │ ← update own
                              can_update_all  │
                              can_delete      │
                              can_delete_all  │

On each protected request:
  1. Get user from JWT (must be is_active=True)
  2. Collect roles via UserRole
  3. Load AccessRule rows for those roles and the view's resource
  4. Run check_access(resource, action, obj_owner_id)
  5. Allow or return 403
```

Views declare requirements with class attributes:

```python
rbac_resource = "task"
rbac_action = "read"   # read | create | update | delete
```

## Database Schema (high level)

See `docs/rbac-schema.md` for full RBAC field types and seed data.

**Users domain:**
- `users_user` — custom user table

**RBAC domain:**
- `rbac_role`
- `rbac_accessrule`
- `rbac_userrole`

**Business domain (Phase 2):**
- `tasks_task`
- `projects_project`
- `tasks_comment`
