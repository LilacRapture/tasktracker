# Architecture Decision Records (ADR)

> Log of all significant technical decisions. Add an entry every time you choose a library, pattern, or approach that isn't obvious.
> Format: date, decision, context, alternatives considered, consequences.

---

## ADR-001 — Custom User Model (AbstractBaseUser)

**Date:** project start  
**Status:** Accepted

**Decision:** Use `AbstractBaseUser` + custom `UserManager` instead of `AbstractUser`.

**Context:** The test assignment requires a custom auth system. We need full control over the user model fields and don't want Django's unused fields (username, first_name/last_name from contrib.auth) mixed with our own schema.

**Alternatives considered:**
- `AbstractUser` — easier, but inherits fields we don't control and couples us to Django's auth conventions
- Custom model from scratch (no abstract base) — too much boilerplate for no benefit

**Consequences:**
- Must implement `get_full_name()`, `get_short_name()`, `has_perm()`, `has_module_perms()` ourselves
- More setup, but total control over schema
- `AUTH_USER_MODEL = 'users.User'` must be set before first migration — cannot change later without reset

---

## ADR-002 — JWT over Session Authentication

**Date:** project start  
**Status:** Accepted

**Decision:** Use `djangorestframework-simplejwt` for auth tokens. Disable session auth entirely.

**Context:** This is an API-only backend. Sessions require cookies and are stateful. JWT is stateless and standard for REST APIs consumed by frontends or mobile clients.

**Alternatives considered:**
- Django sessions — stateful, not appropriate for API-first design
- DRF TokenAuth (built-in) — single static token, no expiry, less secure
- OAuth2 (django-oauth-toolkit) — overkill for this project scope

**Consequences:**
- Access tokens short-lived (e.g. 15 min), refresh tokens longer (7 days)
- Logout requires refresh token blacklisting — SimpleJWT's `TokenBlacklist` app must be in `INSTALLED_APPS`
- Stateless = no server-side session storage needed

---

## ADR-003 — Custom RBAC over Django Built-in Permissions

**Date:** project start  
**Status:** Accepted

**Decision:** Build a custom Role/Permission/UserRole schema instead of using `django.contrib.auth` groups and permissions.

**Context:** The test assignment explicitly requires a self-designed access control system, not one "from the box". Also, Django's built-in permission system is model-centric (per-model CRUD perms), while we need resource+action granularity that maps to API endpoints, not model operations.

**Alternatives considered:**
- `django-guardian` (object-level permissions) — still built on Django's permission model
- Django groups + permissions — explicitly excluded by assignment requirements

**Consequences:**
- Must write a custom DRF `BasePermission` class
- Must write seed management command to populate initial roles/permissions
- More code, but the schema is exactly what we need and demonstrates understanding

---

## ADR-004 — Soft Delete via is_active=False

**Date:** project start  
**Status:** Accepted

**Decision:** User account deletion sets `is_active=False` and logs the user out. No hard delete.

**Context:** Assignment requirement. Preserves audit trail and avoids FK integrity issues.

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
