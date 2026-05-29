# Architecture Overview — TaskTracker

## System Purpose

TaskTracker is an API-only backend that provides:
1. Custom authentication (JWT-based, stateless)
2. Custom RBAC (role-based access control) with its own DB schema
3. Task and project management as the business domain

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Framework | Django 5 + Django REST Framework |
| Auth tokens | djangorestframework-simplejwt |
| Database | PostgreSQL 16 |
| Config | python-decouple (.env) |
| Containerization | Docker + docker-compose |
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
│   │   ├── models.py        # User (AbstractBaseUser)
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
│   │   ├── models.py        # Role, Permission, RolePermission, UserRole
│   │   ├── permissions.py   # DRF permission class (RBACPermission)
│   │   ├── middleware.py    # Optional: attach user roles to request
│   │   ├── views.py         # Admin API to manage roles/permissions
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
│   ├── rbac-schema.md       # RBAC DB schema description
│   └── api.md               # Endpoint reference
│
├── AGENTS.md                # AI agent instructions
├── .cursor/rules/project.mdc
├── .env.example
├── docker-compose.yml
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
    ├── RBACPermission (custom, checks Role→Permission chain)
    │       └── 403 if user lacks required permission
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

## RBAC Flow

```
User ──has──► UserRole ──points to──► Role
                                        │
                                        └──has──► RolePermission ──points to──► Permission
                                                                                    │
                                                                          resource: "task"
                                                                          action:   "read"

On each request:
  1. Get user from JWT
  2. Get user's roles via UserRole
  3. Get permissions for those roles via RolePermission
  4. Check if required permission (resource:action) is in the set
  5. Allow or return 403
```

## Database Schema (high level)

See `docs/rbac-schema.md` for full RBAC schema with field types.

**Users domain:**
- `users_user` — custom user table

**RBAC domain:**
- `rbac_role`
- `rbac_permission`
- `rbac_rolepermission` (M2M)
- `rbac_userrole` (M2M)

**Business domain (Phase 2):**
- `tasks_task`
- `projects_project`
- `tasks_comment`
