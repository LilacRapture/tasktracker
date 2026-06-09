# Architecture Decision Records (ADR)

> Log of all significant technical decisions. Add an entry every time you choose a library, pattern, or approach that isn't obvious.
> Format: date, decision, context, alternatives considered, consequences.

---

## ADR-001 — Custom User Model (AbstractBaseUser)

**Date:** project start  
**Status:** Accepted

**Decision:** Use `AbstractBaseUser` + `PermissionsMixin` + custom `UserManager` instead of `AbstractUser`.

**Context:** TaskTracker is API-first with email-based login. We need explicit control over user fields (name parts, email as identifier) and want to avoid Django's default username-centric schema and unused `AbstractUser` baggage.

**Alternatives considered:**
- `AbstractUser` — easier, but inherits fields we don't control and couples us to Django's auth conventions
- `AbstractBaseUser` alone — no `is_superuser` / admin helpers without reimplementing them
- Custom model from scratch (no abstract base) — too much boilerplate for no benefit

**Consequences:**
- `PermissionsMixin` supplies `is_superuser`, `has_perm()`, and `has_module_perms()` for **Django admin only** — not for API RBAC
- Must implement `get_full_name()` and `get_short_name()` on the User model (or via properties)
- `AUTH_USER_MODEL = 'users.User'` must be set before first migration — cannot change later without reset

---

## ADR-002 — JWT over Session Authentication (API)

**Date:** project start  
**Status:** Accepted

**Decision:** Use `djangorestframework-simplejwt` for API auth. Do not use session or cookie auth on DRF views.

**Context:** This is an API-first backend. JWT is stateless and standard for REST clients. Django's session stack may remain in `INSTALLED_APPS` for the built-in admin site at `/admin/`.

**Alternatives considered:**
- Django sessions for API — stateful, cookie-based, poor fit for SPA/mobile clients
- DRF TokenAuth (built-in) — single static token, no expiry, less secure
- OAuth2 (django-oauth-toolkit) — overkill for this project scope

**Consequences:**
- Access tokens short-lived (e.g. 15 min), refresh tokens longer (7 days)
- Logout requires refresh token blacklisting — SimpleJWT's `TokenBlacklist` app must be in `INSTALLED_APPS`
- API clients send `Authorization: Bearer <access_token>`; no session cookie for `/api/*`

---

## ADR-003 — AccessRule RBAC over Django Built-in Permissions

**Date:** project start  
**Status:** Accepted

**Decision:** Build a custom `Role` / `AccessRule` / `UserRole` schema (see `docs/rbac-schema.md`) instead of using `django.contrib.auth` groups and permissions for API access control.

**Context:** API endpoints are authorized by resource and action (e.g. `task:read`) with optional ownership tiers (`can_read` vs `can_read_all`, etc.). Django's built-in permissions are model-centric (add/change/delete per model) and don't map cleanly to that model.

**Alternatives considered:**
- Flat `Permission` table with `resource:action` strings and `RolePermission` M2M — simpler on paper, but no first-class ownership flags; superseded by AccessRule design
- `django-guardian` (object-level permissions) — still built on Django's permission model
- Django groups + permissions — model-centric CRUD flags; no first-class ownership tiers per resource

**Consequences:**
- Implement `check_access()` and DRF `RBACPermission` (see rbac-schema)
- Seed management command for roles and AccessRule rows
- Admin API under `/api/rbac/` for roles and rules; user role assignment under `/api/users/{id}/roles/`

---

## ADR-004 — Soft Delete via is_active=False

**Date:** project start  
**Status:** Accepted

**Decision:** User account deletion sets `is_active=False` and logs the user out. No hard delete.

**Context:** User-initiated account deletion should preserve historical data and avoid FK integrity issues. Setting `is_active=False` keeps the record for audit while blocking login.

**Consequences:**
- Login must check `is_active=True`
- User appears deleted to themselves but record stays in DB
- Need to filter `is_active=False` users from any listings

---

## ADR-005 — python-decouple for Config

**Date:** project start  
**Status:** Accepted

**Decision:** Use `python-decouple` to read all settings from `.env` file.

**Alternatives considered:**
- `django-environ` — similar, but decouple is simpler and not Django-specific
- `os.environ` directly — no type casting, no `.env` file support out of the box

---

## ADR-006 — Python 3.12 Version Pin

**Date:** 2026-05-31  
**Status:** Accepted

**Decision:** Standardize on Python 3.12.x for local dev, CI, and future Docker. Pin via `.python-version` and `pyproject.toml` (`requires-python = ">=3.12,<3.13"`).

**Context:** Development on Python 3.14 caused problems with Django admin forms. Django 5.0.x and the current dependency set are validated on 3.12 for this project.

**Alternatives considered:**
- Python 3.14 — admin issues; too bleeding-edge for stable portfolio work
- Unpinned “latest Python” — inconsistent environments across machines

**Consequences:**
- Recreate virtualenv with `python3.12` after clone or upgrade
- Phase 2 Docker image should use `python:3.12-slim` (or similar)
- Upgrade to 3.13+ only after Django/deps explicitly support it and admin is verified

---

## Template for new ADRs

```
## ADR-00N — Title

**Date:**  
**Status:** Accepted / Superseded by ADR-00X / Deprecated

**Decision:**

**Context:**

**Alternatives considered:**

**Consequences:**
```
