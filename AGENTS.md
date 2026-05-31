# AGENTS.md — AI Agent Instructions

> This file is the single source of truth for any AI agent (Cursor, Claude, Copilot) working on this project.
> Read it fully before making any changes.

---

## Project Overview

**Name:** TaskTracker  
**Purpose:** Portfolio project + test assignment  
**What it is:** A task/project management backend with a custom authentication and RBAC (role-based access control) system.  
**Stack:** Python 3.12, Django 5, Django REST Framework, PostgreSQL, SimpleJWT

---

## Current Phase

**Phase 1 — Test Assignment (active)**
- Custom auth system (register, login, logout, soft delete)
- Custom RBAC (Role, AccessRule, UserRole — see `docs/rbac-schema.md`)
- Mock views for business objects (tasks, projects)
- DRF API for admin to manage roles and access rules

**Phase 2 — Portfolio Extension (after Phase 1)**
- Real Task and Project models with full CRUD
- Filtering, pagination, search
- Tests, Swagger docs (drf-spectacular)
- Docker + deploy

---

## Architecture Rules (always follow these)

1. **Custom User model only.** Never use `django.contrib.auth.models.User`. Our user is in `apps/users/models.py` extending `AbstractBaseUser`.
2. **Custom RBAC only.** Never use Django's built-in `Permission` or `Group` for API access control. Our system lives in `apps/rbac/` (`Role`, `AccessRule`, `UserRole`). The User model may use `PermissionsMixin` **only** so Django admin works (`is_superuser`, `is_staff`); do not call `user.has_perm()` for API authorization — use `check_access()` / `RBACPermission` instead.
3. **JWT auth for the API.** Clients authenticate with `Authorization: Bearer <token>` via `djangorestframework-simplejwt`. DRF must not use session authentication on API views. Django's session middleware may remain for the built-in admin site only.
4. **App separation.** Each Django app has a single responsibility:
   - `users` — User model, profile CRUD
   - `auth_core` — login, logout, register, token endpoints
   - `rbac` — Role, AccessRule, UserRole models + enforcement logic
   - `tasks` — Task business logic (Phase 2, mock in Phase 1)
   - `projects` — Project business logic (Phase 2, mock in Phase 1)
5. **Config lives in `config/`.** Not in any app. `settings.py`, `urls.py`, `wsgi.py` are all there.
6. **Env vars for secrets.** Never hardcode DB credentials, secret keys, or JWT secrets. Use `.env` + `python-decouple`.
7. **Python 3.12 only.** Pinned in `.python-version` and `pyproject.toml` (`requires-python = ">=3.12,<3.13"`). Do not use 3.13+ — Django admin issues were seen on 3.14. Match 3.12 locally and in CI/Docker when added.

Cursor-specific reminders live in `.cursor/rules/project.mdc` (summary only — `AGENTS.md` remains the full spec).

---

## Key Decisions Log

See `docs/decisions.md` for full ADR history.  
Short version:
- AbstractBaseUser + PermissionsMixin (admin only) — control over fields, admin compatibility
- JWT over sessions for API — stateless, better for API-first
- AccessRule-based RBAC — ownership-aware rules per role per resource (`docs/rbac-schema.md`)
- Soft delete via `is_active=False` — data retention, audit trail

---

## RBAC System Summary

**Canonical spec:** `docs/rbac-schema.md` — implement exactly as documented there.

Short version:
- `Role` — named role (`admin`, `manager`, `developer`, `viewer`)
- `AccessRule` — one row per role per resource; boolean flags (`can_read`, `can_read_all`, `can_create`, etc.) with optional ownership checks
- `UserRole` — which roles a user has
- `check_access(user, resource, action, obj_owner_id=None)` — core check (see rbac-schema)
- `RBACPermission` in `apps/rbac/permissions.py` — DRF class; views set `rbac_resource` and `rbac_action`

---

## HTTP Error Conventions

- **401 Unauthorized** — token missing or invalid → user not identified
- **403 Forbidden** — user identified but lacks required resource+action access
- Never return 404 when the real reason is 403 (do not leak resource existence)

---

## Code Style

- Follow PEP8, use type hints on all function signatures
- Docstrings on all models and non-trivial methods
- No business logic in views — views call services or serializers
- Serializers validate; views orchestrate; models store
- Prefer class-based views (APIView or ModelViewSet) over function-based
- No `print()` for debugging — use `logging`

---

## What NOT to Do

- Do not run `python manage.py startapp` — apps are already scaffolded
- Do not add dependencies without updating `requirements.txt` and `docs/decisions.md`
- Do not modify migrations manually
- Do not hardcode secrets

---

## Project Status

### Done
- [x] Project structure scaffolded
- [x] Custom User model (model, manager, admin, initial migration)
- [x] Auth endpoints (register, login, logout, refresh)
- [x] RBAC models, `seed_roles`, `check_access()`, `RBACPermission`
- [x] User profile endpoints (`/users/me/`, list, detail)
- [x] RBAC admin API (roles, access rules, user role assignment)

### In Progress
- [ ] Mock task/project views (Phase 1 — last item)

### Later (Phase 2)
- [ ] Docker + deploy (`docker-compose.yml` exists but is not configured yet)
- [ ] Real Task/Project CRUD, tests, Swagger

### Open Questions
- Nothing yet
