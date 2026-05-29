# AGENTS.md — AI Agent Instructions

> This file is the single source of truth for any AI agent (Cursor, Claude, Copilot) working on this project.
> Read it fully before making any changes.

---

## Project Overview

**Name:** TaskTracker  
**Purpose:** Portfolio project + test assignment  
**What it is:** A task/project management backend with a custom authentication and RBAC (role-based access control) system.  
**Stack:** Django 5, Django REST Framework, PostgreSQL, SimpleJWT, Docker

---

## Current Phase

**Phase 1 — Test Assignment (active)**
- Custom auth system (register, login, logout, soft delete)
- Custom RBAC (roles, permissions, resources — NOT django.contrib.auth groups/permissions)
- Mock views for business objects (tasks, projects)
- DRF API for admin to manage roles/permissions

**Phase 2 — Portfolio Extension (after Phase 1)**
- Real Task and Project models with full CRUD
- Filtering, pagination, search
- Tests, Swagger docs (drf-spectacular)
- Docker + deploy

---

## Architecture Rules (always follow these)

1. **Custom User model only.** Never use `django.contrib.auth.models.User`. Our user is in `apps/users/models.py` extending `AbstractBaseUser`.
2. **Custom RBAC only.** Never use Django's built-in `Permission` or `Group` models for access control. Our system lives in `apps/rbac/`.
3. **JWT auth.** Sessions are disabled. Auth via `Authorization: Bearer <token>` header using `djangorestframework-simplejwt`.
4. **App separation.** Each Django app has a single responsibility:
   - `users` — User model, profile CRUD
   - `auth_core` — login, logout, register, token endpoints
   - `rbac` — Role, Permission, UserRole models + enforcement logic
   - `tasks` — Task business logic (Phase 2, mock in Phase 1)
   - `projects` — Project business logic (Phase 2, mock in Phase 1)
5. **Config lives in `config/`.** Not in any app. `settings.py`, `urls.py`, `wsgi.py` are all there.
6. **Env vars for secrets.** Never hardcode DB credentials, secret keys, or JWT secrets. Use `.env` + `python-decouple`.

---

## Key Decisions Log

See `docs/decisions.md` for full ADR history.  
Short version:
- AbstractBaseUser over AbstractUser — more control, no unused fields
- JWT over sessions — stateless, better for API-first
- Custom permission tables over Django built-in — requirement + more flexible
- Soft delete via `is_active=False` — data retention, audit trail

---

## RBAC System Summary

See `docs/rbac-schema.md` for full schema.  
Short version:
- `Role` — named role (admin, manager, developer, viewer)
- `Permission` — a resource+action pair (e.g. task:read, project:delete)
- `RolePermission` — which permissions a role has
- `UserRole` — which roles a user has
- Custom DRF permission class in `apps/rbac/permissions.py` checks this chain on every request

---

## HTTP Error Conventions

- **401 Unauthorized** — token missing or invalid → user not identified
- **403 Forbidden** — user identified but lacks permission for this resource+action
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
- [ ] Project structure scaffolded

### In Progress
- [ ] Custom User model

### Open Questions
- Nothing yet
