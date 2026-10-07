# Architecture Decision Records (ADR)

> Only decisions with real alternatives and non-obvious trade-offs. Routine fixes, dependency bumps, and library choices without a real alternative don't get an ADR.
> Keep each entry ≤ 15 lines; omit sections with nothing to add. Consequences = constraints on future work and revisit triggers, not a changelog (files touched, deps added → commit message).
> Numbers are permanent and never reused; gaps (005, 008, 010) are entries removed as not ADR-worthy — see git history.

---

## ADR-001 — Custom User Model (AbstractBaseUser)

**Date:** project start  
**Status:** Accepted

**Decision:** `AbstractBaseUser` + `PermissionsMixin` + custom `UserManager`, instead of `AbstractUser`.

**Context:** API-first with email login; we want explicit control over user fields (name parts) without Django's username-centric schema.

**Alternatives:**
- `AbstractUser` — easier, but inherits fields we don't control.
- `AbstractBaseUser` alone — no `is_superuser` / admin helpers without reimplementing them.
- Model from scratch, no abstract base — too much boilerplate.

**Consequences:**
- `PermissionsMixin` (`is_superuser`, `has_perm()`) serves **Django admin only**, not API RBAC.
- `AUTH_USER_MODEL` had to be set before the first migration; changing it later requires a reset.

---

## ADR-002 — JWT over Session Authentication (API)

**Date:** project start  
**Status:** Accepted

**Decision:** `djangorestframework-simplejwt` for API auth; no session/cookie auth on DRF views.

**Context:** Stateless JWT fits an API-first backend. The session stack stays enabled only for `/admin/`.

**Alternatives:**
- Django sessions — stateful, poor fit for SPA/mobile clients.
- DRF TokenAuth — single static token, no expiry.
- OAuth2 (django-oauth-toolkit) — overkill for this scope.

**Consequences:** Logout requires refresh-token blacklisting, so SimpleJWT's `token_blacklist` app must stay in `INSTALLED_APPS`.

---

## ADR-003 — AccessRule RBAC over Django Built-in Permissions

**Date:** project start  
**Status:** Accepted

**Decision:** Custom `Role` / `AccessRule` / `UserRole` schema (see `docs/rbac-schema.md`) instead of `django.contrib.auth` groups and permissions for API access.

**Context:** Endpoints are authorized by resource and action (`task:read`) with ownership tiers (`can_read` vs `can_read_all`). Django's permissions are model-centric (add/change/delete) and don't map to that.

**Alternatives:**
- Flat `resource:action` permission table with `RolePermission` M2M — no first-class ownership flags.
- `django-guardian` — object-level, but still built on Django's permission model.
- Django groups + permissions — no ownership tiers per resource.

**Consequences:** We own the enforcement code (`check_access()`, `RBACPermission`) and the seed data; the spec lives in `docs/rbac-schema.md`.

---

## ADR-004 — Soft Delete via is_active=False

**Date:** project start  
**Status:** Accepted

**Decision:** Account deletion sets `is_active=False` and logs the user out. No hard delete.

**Context:** Preserves history and avoids FK integrity issues while blocking login.

**Consequences:** Login and every user listing/lookup must filter on `is_active=True`.

---

## ADR-006 — Python 3.12 Version Pin

**Date:** 2026-05-31  
**Status:** Accepted

**Decision:** Python 3.12.x for local dev, CI, and Docker, pinned in `.python-version` and `pyproject.toml` (`requires-python = ">=3.12,<3.13"`).

**Context:** Python 3.14 broke Django admin forms; Django 5.0.x and the current dependencies are validated on 3.12.

**Alternatives:**
- Python 3.14 — admin issues, too bleeding-edge.
- Unpinned "latest" — inconsistent environments across machines.

**Consequences:** Upgrade to 3.13+ only after Django and dependencies officially support it and admin is verified.

---

## ADR-007 — No project-ownership check on Task.project assignment

**Date:** 2026-06-12  
**Status:** Accepted

**Decision:** `TaskWriteSerializer` accepts any existing `project` id. It does not check that the user may modify the target project.

**Context:** A `validate_project` restricting task→project linking was considered. With the current seed roles, every role with `task:create` also has `project:read_all`, so the restriction would have no effect today.

**Consequences:** Revisit if a role gets `task:create` together with `project:read` (own only, no `_all`): add `validate_project` using `get_accessible_queryset(user, "project", "read", Project.objects.all())` so unseen project ids can't be referenced.

---

## ADR-009 — generics.ListCreateAPIView + PageNumberPagination for Task/Project lists

**Date:** 2026-06-14  
**Status:** Accepted

**Decision:** `TaskListView` and `ProjectListView` become `generics.ListCreateAPIView`. RBAC row filtering moves into `get_queryset()` via `get_accessible_queryset(...)`. Pagination is global: `PageNumberPagination`, `PAGE_SIZE = 20`.

**Context:** Filtering, pagination, search, and drf-spectacular all work better with generics than with a bare `APIView`.

**Alternatives:** Manual `PageNumberPagination` inside `APIView.get()` — duplicates what generics provide and doesn't help filtering or schema generation.

**Consequences:**
- List responses are `{"count", "next", "previous", "results"}`.
- `TaskListView.create()` is overridden because read and write use different serializers.
- Detail views stay plain `APIView` (no pagination needed).
- `UserListView` and the RBAC lists still return flat arrays — inconsistent until addressed (see "Later" in `AGENTS.md`).

---

## ADR-011 — drf-spectacular for OpenAPI schema & Swagger UI

**Date:** 2026-06-14  
**Status:** Accepted

**Decision:** `drf-spectacular` generates the OpenAPI 3 schema, served at `/api/schema/`, `/api/docs/` (Swagger UI), `/api/redoc/`.

**Context:** Plain `APIView` classes without `serializer_class` can't be introspected, so those views are annotated with `@extend_schema`.

**Consequences:**
- `apps/common/schema.py` holds shared `ErrorResponse` / `DetailResponse` shapes for the `{"error"}` / `{"detail"}` conventions.
- `ENUM_NAME_OVERRIDES` separates `Task.status` from `Project.status`; explicit `operation_id` on `RoleListView.get` and `UserListView.get` avoids `*_retrieve` name collisions.
- CI runs `spectacular --validate --fail-on-warn`: a new unannotated view or enum collision fails the build.
- View and serializer docstrings become Swagger descriptions, so write them for API consumers.
- `schema.yaml` is generated and not committed.

---

## ADR-012 — No object-level check on role/access_rule/user admin endpoints

**Date:** 2026-06-14  
**Status:** Accepted

**Decision:** Role, AccessRule, UserRole, and User list/detail views rely only on `RBACPermission.has_permission()` (`has_any_access`). `has_object_permission()` / `check_access()` with `obj_owner_id` is not used.

**Context:** `has_any_access()` passes if either the own or the `_all` flag is set. For task/project, `get_accessible_queryset()` / `check_access(obj_owner_id=...)` then narrow to own objects. For `role`, `access_rule`, and `user` "own" is undefined, so endpoint access means access to all objects. This is harmless today: in the seed data `can_X` equals `can_X_all` for these resources.

**Consequences:** Before adding a role with `can_X` (own) but not `can_X_all` on these resources, either add object-level scoping, or treat the own flag as disallowed for them and document it in `docs/rbac-schema.md`. Otherwise that role gets full access to all roles, rules, assignments, and profiles.

---

## ADR-013 — Docker deploy: gunicorn + whitenoise, migrations in entrypoint

**Date:** 2026-06-15  
**Status:** Accepted

**Decision:** `web` runs under gunicorn; static files are served by whitenoise from the same container (no nginx). `entrypoint.sh` waits for Postgres, then runs `migrate`, `seed_roles`, `collectstatic`.

**Context:** One-command `docker-compose up --build` demo; a reverse proxy is disproportionate for this scope.

**Alternatives:**
- nginx for static/media — more production-like, but needs a second Dockerfile and a shared volume for a small static set.
- Separate one-off `migrate` service — the right pattern for multi-replica `web`, unnecessary for one instance.
- Manual `migrate` — breaks the one-command demo and is easy to forget.

**Consequences:**
- `seed_roles` runs on every start; safe because it's idempotent.
- Revisit migrations-in-entrypoint if `web` is ever scaled beyond one replica.
- Postgres is reachable only on the compose network; `DB_HOST=db` is set in compose, `.env` keeps `localhost` for non-Docker runs.
- nginx was added later for WS routing (ADR-017); static files are still served by whitenoise.

---

## ADR-014 — Realtime transport: Django Channels + WS envelope + ticket auth

**Date:** 2026-07-28  
**Status:** Accepted

**Decision:** `channels` + `channels-redis` in a separate ASGI process next to gunicorn. Three parts designed as one unit:
1. One endpoint `/ws/tasktracker/` carrying all events in a versioned envelope `{"v", "type", "payload"}`.
2. Per-user groups (`user_{id}`). On each task write the backend computes who may read the task via the existing RBAC rules and sends to each user's group.
3. Auth via a one-time ticket (`POST /api/auth/ws-ticket/`, ~20 s TTL, stored in Redis) instead of the access token in the URL.

**Context:** Browser WebSocket can't send an `Authorization` header, so a credential must travel in the URL, and URLs get logged by proxies.

**Alternatives:**
- Access token in the query string — simplest, but leaks into proxy/access logs.
- Per-project groups — `Task.project` is nullable (`SET_NULL`), so project-less tasks need special handling.
- Broadcast to everyone, filter on the client — an RBAC leak: a viewer would receive payloads of tasks they can't read.
- Separate endpoints per stream (`/ws/tasks/`, `/ws/presence/`) — one connection is simpler for client reconnect logic.

**Consequences:**
- Redis is a hard dependency (channel layer + tickets).
- Broadcasts are explicit calls on write paths (serializer create/update, view delete), not `post_save` signals, so the side effect is visible at the call site.
- Recipient computation costs extra queries on every write (see ADR-015).
- Ticket get+delete is not atomic; the race window is accepted. Revisit with an atomic `GETDEL` if this ever needs to be airtight.

---

## ADR-015 — Broadcast recipients computed in two queries, duplicating check_access precedence

**Date:** 2026-07-28  
**Status:** Accepted

**Decision:** `broadcaster._users_with_task_access()` finds recipients with two set-based queries (`can_read_all` holders + the task owner if they hold `can_read`) instead of calling `check_access()` per active user.

**Context:** Per-user `check_access()` costs O(2N+1) queries per broadcast (N = active users), which dominated every task write.

**Alternatives:**
- `check_access()` per user — single source of truth, but linear query growth.
- Redis cache of `can_read_all` holders — needs invalidation on role/rule changes; deferred.

**Consequences:**
- The read-precedence rule now lives in two places: `check_access()` (canonical) and `_users_with_task_access()`. Change both if the access model in `docs/rbac-schema.md` changes.
- Scoped to `task`; extending broadcasts to other resources needs a generalized helper.
- `.distinct()` guards against duplicates when a user has several qualifying roles (regression test exists).
- A cache, if added later, layers on top of the same two queries.

---

## ADR-016 — Presence via connect/disconnect only, no Redis heartbeat

**Date:** 2026-07-28  
**Status:** Accepted

**Decision:** `presence.joined` / `presence.left` come purely from WS `connect()` / `disconnect()`, broadcast to one shared group. No TTL/heartbeat state.

**Alternatives:** Redis TTL heartbeat — survives ASGI restarts and enables REST presence queries, but adds a client heartbeat protocol, state that can diverge from the real connection, and time-dependent tests.

**Consequences:**
- A client that vanishes without a close frame may stay shown as online. Accepted: it's an indicator, not task data.
- After an ASGI restart presence is empty until clients reconnect.
- `editing_started` / `editing_stopped` reuse `_users_with_task_access` for recipients.
- Revisit if presence proves unreliable across deploys.

---

## ADR-017 — nginx reverse proxy + CORS for the separate SvelteKit frontend

**Date:** 2026-08-01  
**Status:** Accepted

**Decision:** nginx in front of two processes: `web` (gunicorn/WSGI) and `web_ws` (daphne/ASGI), routing `/ws/` to ASGI and the rest to WSGI. `django-cors-headers` with an explicit `CORS_ALLOWED_ORIGINS` whitelist.

**Context:** The frontend decision made both concrete; nginx is the natural place to route between the two backends behind one port.

**Alternatives:**
- One container running gunicorn and daphne via supervisord — needs Dockerfile/entrypoint changes for a saving that doesn't matter at this scale.
- `CORS_ALLOW_ALL_ORIGINS = True` — an explicit whitelist costs one `.env` line.

**Consequences:**
- `web` and `web_ws` share the image and `entrypoint.sh`, so `migrate` / `seed_roles` / `collectstatic` run twice concurrently on startup. Accepted since they're idempotent; add a lighter entrypoint for `web_ws` if it ever races.
- Only nginx publishes a port (`8000:80`); local URLs stay `http://localhost:8000/api/...`.
- `CORS_ALLOWED_ORIGINS` defaults to `http://localhost:5173`; production origins must be added explicitly.

---

## Template for new ADRs

```
## ADR-0NN — Title

**Date:**  
**Status:** Accepted / Superseded by ADR-0XX / Deprecated

**Decision:**

**Context:**

**Alternatives:**

**Consequences:**
```