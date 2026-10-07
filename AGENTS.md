# AGENTS.md — AI Agent Instructions

> Single source of truth for any AI agent working on this project.
> Read it fully before making any changes.

---

## Project Overview

**Name:** TaskTracker  
**Purpose:** Personal project  
**What it is:** A task/project management backend with a custom authentication and RBAC (role-based access control) system.  
**Stack:** Python 3.12, Django 5, Django REST Framework, PostgreSQL, SimpleJWT

---

## Architecture Rules (always follow these)

1. **Custom User model only.** Never use `django.contrib.auth.models.User`. Our user is in `apps/users/models.py` extending `AbstractBaseUser`.
2. **Custom RBAC only.** Never use Django's built-in `Permission` or `Group` for API access control. Our system lives in `apps/rbac/` (`Role`, `AccessRule`, `UserRole`). The User model may use `PermissionsMixin` **only** so Django admin works (`is_superuser`, `is_staff`); do not call `user.has_perm()` for API authorization — use `check_access()` / `RBACPermission` instead. Canonical spec: `docs/rbac-schema.md` — implement exactly as documented there. Views declare `rbac_resource` and `rbac_action`; enforcement goes through `RBACPermission`.
3. **JWT auth for the API.** Clients authenticate with `Authorization: Bearer <token>` via `djangorestframework-simplejwt`. DRF must not use session authentication on API views. Django's session middleware may remain for the built-in admin site only.
4. **App separation.** Each Django app has a single responsibility:
   - `users` — User model, profile CRUD
   - `auth_core` — login, logout, register, token endpoints
   - `rbac` — Role, AccessRule, UserRole models + enforcement logic
   - `tasks` — Task model and CRUD
   - `projects` — Project model and CRUD
   - `common` — shared DRF helpers (OpenAPI response shapes)
5. **Config lives in `config/`.** Not in any app. `settings.py`, `urls.py`, `wsgi.py` are all there.
6. **Env vars for secrets.** Never hardcode DB credentials, secret keys, or JWT secrets. Use `.env` + `python-decouple`.
7. **Python 3.12 only.** Pinned in `.python-version` and `pyproject.toml` (`requires-python = ">=3.12,<3.13"`). Do not use 3.13+ — Django admin issues were seen on 3.14.

Cursor-specific reminders live in `.cursor/rules/project.mdc` (summary only — `AGENTS.md` remains the full spec).

Why these choices were made: `docs/decisions.md`.

---

## HTTP Error Conventions

- **401 Unauthorized** — token missing or invalid → user not identified (DRF/JWT default: `{"detail": "..."}`)
- **403 Forbidden** — user identified but lacks required access → `RBACPermission` sets `detail` like `"Permission denied. Required: task:read"`
- **400 Bad Request** — validation errors → DRF field errors dict or `{"detail": "..."}`
- Never return 404 when the real reason is 403 on **business resources** (do not leak existence). Admin/RBAC lookup 404s for missing IDs are acceptable in Phase 1.

Response shapes: `docs/api.md`.

---

## Code Style

- Follow PEP8, use type hints on all function signatures
- No business logic in views — views call services or serializers
- Serializers validate; views orchestrate; models store
- Prefer class-based views (APIView or ModelViewSet) over function-based
- No `print()` for debugging — use `logging`
- Comments and docstrings: see the next section

---

## Comments, docstrings, docs

Write only what a reader can't get from the code, the names, or git history.
When in doubt, leave it out.

**Code**
- Comment *why* (constraint, trade-off, gotcha), never *what*. No comments
  narrating the next line; no explaining Django/DRF/stdlib behavior.
- A docstring is optional when the name and fields are self-explanatory.
  Default length: one line. No Args/Returns blocks that repeat type hints.
- View docstrings are published in Swagger (drf-spectacular): write them for
  the API consumer in 1–2 lines. No URL/verb lists, no internals — put those
  in comments.
- Don't restate facts owned elsewhere: role names, permissions, settings
  values (token lifetimes), routes. Link to the source instead.
- No banner/section comments inside classes. Add `logger` only to modules
  that actually log.
- Changing behavior → update or delete the affected docstring in the same
  commit. A wrong comment is worse than none.
- Docstring longer than 3 lines? Ask whether it belongs in `docs/` instead.

**Docs**
- One source of truth per fact; everything else links to it
  (RBAC → `docs/rbac-schema.md`, endpoints → `docs/api.md` / Swagger,
  rules → this file).
- Don't copy code, diagrams, or file trees into docs — they rot.
- ADR only for decisions with real alternatives. Target ≤ 15 lines.
  Consequences = constraints on future work and revisit triggers, not a
  changelog (files touched, deps added → commit message).
- Phase/status checklists live only in this file.

---

## What NOT to Do

- Do not run `python manage.py startapp` — apps are already scaffolded
- Do not add dependencies without updating `requirements.txt` and, if the choice is non-obvious, `docs/decisions.md`
- Do not modify migrations manually
- Do not hardcode secrets

---

## Project Status

### Phase 1 — Done
- [x] Project structure scaffolded
- [x] Custom User model (model, manager, admin, initial migration)
- [x] Auth endpoints (register, login, logout, refresh)
- [x] RBAC models, `seed_roles`, `check_access()`, `RBACPermission`
- [x] User profile endpoints (`/users/me/`, list, detail, soft delete)
- [x] RBAC admin API (roles, access rules, user role assignment)
- [x] Mock task/project views with RBAC

### Phase 2 — Done
- [x] Real Task/Project models and full CRUD
- [x] Filtering, pagination, search
- [x] Tests, Swagger (drf-spectacular)
- [x] Docker + deploy

### Phase 3 (candidates — not committed yet)

- API response shape consistency: `/users/`, `/rbac/roles/`,
  `/rbac/roles/{id}/rules/` still return flat arrays vs. paginated
  `{count, next, previous, results}` for `/tasks/` and `/projects/`
  (see ADR-009)
- Object-level RBAC checks for role/access_rule/user admin endpoints —
  currently endpoint-level only, safe under current seed data (ADR-012)
- nginx/TLS reverse proxy in front of `web` if a real domain is added
  (see ADR-013 consequences)
- CORS config (`django-cors-headers`) if a separate frontend is built

### Open Questions
- Nothing yet