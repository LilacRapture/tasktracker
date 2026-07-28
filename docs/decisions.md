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

## ADR-007 — No project-ownership check on Task.project assignment

**Date:** 2026-06-12
**Status:** Accepted

**Decision:** TaskWriteSerializer accepts any `project` id the requesting
user can read (i.e. any project, since all roles with `task:create` also
have `project:read_all`). No additional check that the user owns or can
modify the target project.

**Context:** Considered adding `validate_project` to restrict task→project
linking to projects the user can modify. Reviewed against current seed
roles (admin, manager, developer, viewer) — no role combination grants
`task:create` alongside a restricted (`project:read` without `_all`) view
of projects, so the restriction would have no effect today and protects
against a hypothetical future role only.

**Consequences:**
- If a future role is introduced with `project:read` (own only, no `_all`)
  combined with `task:create`, revisit this — add `validate_project` using
  `get_accessible_queryset(user, "project", "read", Project.objects.all())`
  to prevent referencing unseen project ids.

---

## ADR-008 — pytest + pytest-django for testing

**Date:** 2026-06-13
**Status:** Accepted

**Decision:** Use pytest with pytest-django instead of Django's built-in
unittest-based TestCase/TestRunner.

**Context:** pytest's fixtures and parametrization fit well with RBAC
testing — the access matrix in `docs/rbac-schema.md` is naturally expressed
as a parametrized table (role × resource × action → expected bool).

**Alternatives considered:**
- `django.test.TestCase` — works fine, but parametrization is more verbose
  (subTest or manual loops)

**Consequences:**
- `pytest.ini` / `pyproject.toml` config needed for `DJANGO_SETTINGS_MODULE`
- Test files: `apps/<app>/tests/test_*.py` or `apps/<app>/tests.py`

---

## ADR-009 — generics.ListCreateAPIView + PageNumberPagination for Task/Project lists

**Date:** 2026-06-14
**Status:** Accepted

**Decision:** Convert `TaskListView` and `ProjectListView` from plain `APIView`
to `generics.ListCreateAPIView`. RBAC row-level filtering moves into
`get_queryset()` via `get_accessible_queryset(...)`. Pagination is enabled
globally via `DEFAULT_PAGINATION_CLASS = PageNumberPagination`,
`PAGE_SIZE = 20`.

**Context:** Phase 2 requires filtering, pagination, and search, plus
drf-spectacular docs later. `generics.ListCreateAPIView` provides pagination
and integrates cleanly with `DjangoFilterBackend` / `SearchFilter` via
`filter_backends`, and gives drf-spectacular a much better starting point for
schema introspection than a bare `APIView`.

**Alternatives considered:**
- Manually instantiate `PageNumberPagination` inside the existing `APIView.get()`
  — works, but duplicates logic that generics already provide and doesn't help
  with filtering/search/schema generation.

**Consequences:**
- Response shape for `GET /tasks/` and `GET /projects/` changes from a plain
  array to `{"count", "next", "previous", "results"}` — `docs/api.md` updated,
  existing tests updated to read `response.json()["results"]`.
- `TaskListView.create()` is overridden directly (rather than relying on
  `CreateModelMixin.create()`) because read (`TaskSerializer`) and write
  (`TaskWriteSerializer`) use different serializers with different shapes.
- Detail views (`TaskDetailView`, `ProjectDetailView`) remain plain `APIView` —
  pagination doesn't apply to single-object responses, no change needed there.
- `UserListView` is not yet converted and still returns a flat array — response
  shape is inconsistent between `/users/` and `/tasks/` / `/projects/` until
  that's addressed in a future change.

---

## ADR-010 — django-filter + DRF SearchFilter/OrderingFilter for Task/Project lists

**Date:** 2026-06-14
**Status:** Accepted

**Decision:** Add `django-filter` and use DRF's built-in `SearchFilter` /
`OrderingFilter` for `GET /api/tasks/` and `GET /api/projects/`, configured
via `DEFAULT_FILTER_BACKENDS` and per-view `filterset_class` /
`search_fields` / `ordering_fields`.

**Context:** Phase 2 requires filtering, pagination, and search. The list
views were already converted to `generics.ListCreateAPIView` (ADR-009),
which makes these backends a one-line addition per view.

**Consequences:**
- Filters/search/ordering operate on the queryset returned by
  `get_queryset()`, i.e. *after* `get_accessible_queryset()` has applied
  RBAC row-level filtering — filters can only narrow, never expand, what a
  user can see.
- `docs/api.md` updated with the new query params.
- `django_filters` added to `INSTALLED_APPS` and `requirements.txt`.

---

## ADR-011 — drf-spectacular for OpenAPI schema & Swagger UI

**Date:** 2026-06-14
**Status:** Accepted

**Decision:** Enable `drf-spectacular` for OpenAPI 3 schema generation, served
via `/api/schema/`, `/api/docs/` (Swagger UI), `/api/redoc/` (ReDoc).

**Context:** Plain `APIView` classes without `serializer_class` can't be
auto-introspected by drf-spectacular ("unable to guess serializer"). All such
views (`auth_core`, `users`, `rbac`, and the Task/Project detail views) were
annotated with `@extend_schema(request=..., responses=...)`.

**Consequences:**
- New shared module `apps/common/schema.py` — `ErrorResponseSerializer` /
  `DetailResponseSerializer` (`inline_serializer`) for the project's
  `{"error": "..."}` / `{"detail": "..."}` response conventions, reused
  across `users`, `rbac`, `tasks`, `projects`.
- `ENUM_NAME_OVERRIDES` in `SPECTACULAR_SETTINGS` disambiguates `Task.status`
  vs `Project.status` enums (`TaskStatusEnum` / `ProjectStatusEnum`).
- Explicit `operation_id` set on `RoleListView.get` and `UserListView.get`
  to resolve `*_retrieve` naming collisions with their detail views.
- `manage.py spectacular --validate --fail-on-warn` added to CI to catch
  schema regressions (new unannotated views, enum collisions, etc.).
- `schema.yaml` is a generated artifact, not committed (`.gitignore`).

---

## ADR-012 — No object-level check on role/access_rule/user-roles admin endpoints

**Date:** 2026-06-14
**Status:** Accepted

**Decision:** RoleListView/DetailView, AccessRuleListView/DetailView,
UserRoleListView/DetailView and UserDetailView/UserListView rely only on
RBACPermission.has_permission() (i.e. has_any_access — can_X OR can_X_all)
for authorization. has_object_permission() / check_access() with
obj_owner_id is not used for these views.

**Context:** has_any_access() grants endpoint access if EITHER the "own"
or the "_all" flag is set for (resource, action). For task/project this is
fine because get_accessible_queryset() / check_access(obj_owner_id=...)
narrows results to "own" objects afterwards. For role/access_rule/user
resources there is no meaningful per-object "owner" concept, so no such
narrowing happens — endpoint access ⇒ access to ALL objects of that type.

Reviewed against current seed roles (docs/rbac-schema.md): for "role",
"access_rule" and "user" resources, can_X and can_X_all are always equal
(both True for admin, both False otherwise — except "user"/read where
admin and manager have both True). So has_any_access() currently behaves
identically to "has can_X_all", and the gap has no effect today.

**Consequences:**
- If a future role grants can_read/update/delete=True (own) with
  can_read/update/delete_all=False on "role", "access_rule" or "user",
  that role would get FULL access to all roles/rules/user-role
  assignments/profiles via these endpoints — not just "its own", since
  "own" is undefined for these resources.
- Before introducing such a role, either (a) add object-level checks /
  scoping for these endpoints, or (b) treat can_X (own, without _all) as
  meaningless/disallowed for resources "role", "access_rule", "user" and
  document that in docs/rbac-schema.md.

---

## ADR-013 — Docker deploy: gunicorn + whitenoise + entrypoint-driven migrations

**Date:** 2026-06-15
**Status:** Accepted

**Decision:** Run the `web` service via `gunicorn` (not `manage.py runserver`).
Static files (admin, Swagger UI) are served by `whitenoise`
(`WhiteNoiseMiddleware` + `STORAGES["staticfiles"]` =
`CompressedManifestStaticFilesStorage`) from inside the same container —
no separate nginx service. An `entrypoint.sh` in the image waits for
Postgres (`pg_isready`), runs `manage.py migrate`, `manage.py seed_roles`,
and `manage.py collectstatic`, then `exec`s the container's CMD
(`gunicorn ...`).

In `docker-compose.yml`: `db` gets a `pg_isready` healthcheck; `web`
depends on it via `condition: service_healthy`. `DB_HOST` is overridden
to `db` via `environment:` on `web` (the shared `.env` keeps
`DB_HOST=localhost` for non-Docker local runs). The bind mount `.:/app`
and the published `5432` port on `db` were removed — `web` runs from the
image's copy of the code, and Postgres is only reachable on the internal
compose network.

**Context:** `docker-compose.yml` existed but was unconfigured
(`command: runserver`, no Dockerfile, `DEBUG`-only static serving, no
migration step). Needed a one-command (`docker-compose up --build`) deploy
suitable for a portfolio demo without introducing infrastructure that's
disproportionate to the project's scope.

**Alternatives considered:**
- nginx reverse proxy serving static/media from a shared volume — more
  "production-grade" and would demonstrate multi-container orchestration,
  but adds a second Dockerfile/config and a shared volume for one small
  admin/Swagger static set; deferred, can be added later (e.g. alongside
  TLS/a real domain) without changing the Django-side setup.
- Separate one-off `migrate` service / init container with
  `depends_on: condition: service_completed_successfully` — the "correct"
  pattern for multi-replica `web`, but unnecessary for a single instance;
  adds a second service definition for no current benefit.
- Manual migration step (`docker-compose exec web python manage.py
  migrate`) — simplest to implement, but breaks the "one command starts
  everything" demo experience and is easy to forget.

**Consequences:**
- `requirements.txt`: added `gunicorn`, `whitenoise`.
- New files: `Dockerfile`, `entrypoint.sh`, `.dockerignore`.
- `config/settings.py`: added `WhiteNoiseMiddleware` (right after
  `SecurityMiddleware`), `STATIC_ROOT`, `STORAGES["staticfiles"]`.
  `DEFAULT_AUTO_FIELD` moved out of the (now reworked) "Static files"
  comment block into its own section — no behavior change, just
  relocated.
- `.env.example`: documented that `DB_HOST=localhost` is for non-Docker
  runs and is overridden to `db` in `docker-compose.yml`.
- `seed_roles` runs on every container start; safe because it's
  idempotent (`get_or_create` / `update_or_create`).
- README should be updated with the `docker-compose up --build` flow as
  the recommended setup path (alongside the existing local/venv
  instructions).
- If a custom domain + TLS is added later, this likely warrants its own
  ADR (nginx/Traefik/Caddy as reverse proxy in front of `web`).

---

## ADR-014 — Realtime transport: Django Channels + WS envelope + ticket-based auth

**Date:** 2026-07-28
**Status:** Accepted

**Decision:** Add `django-channels` + `channels-redis` for WebSocket
support, running as a separate ASGI process alongside the existing
gunicorn/WSGI deployment (see Consequences for deploy implications,
tracked separately). Three sub-decisions bundled together since they
were designed and will evolve as one unit:

1. **Single WS endpoint, envelope format.** One endpoint
   (`/ws/tasktracker/`) carries all event types via a versioned envelope:
   `{"v": 1, "type": "task.updated", "payload": {...}}`. Rejected
   separate per-stream endpoints (`/ws/tasks/`, `/ws/presence/`) —
   presence and task events belong to the same "board" concept, and a
   single connection is simpler for the frontend's reconnect logic.

2. **Per-user channel groups (`user_{id}`), not per-project groups.**
   On any task create/update/delete, the backend computes the list of
   users who can see that object via the EXISTING `get_accessible_queryset`
   / `check_access` (apps/rbac/permissions.py) and broadcasts to each
   user's personal group. Rejected per-project groups — `Task.project`
   is nullable (`SET_NULL`), so project-less tasks would need special-case
   handling; rejected client-side filtering entirely — sending
   unfiltered events to all connected clients and trusting the frontend
   to hide them is a real data leak (a viewer would receive task
   payloads for tasks they have no RBAC access to, even if the UI never
   renders them).

3. **One-time WS ticket instead of a raw access token in the query
   string.** Browsers' native WebSocket API cannot send custom headers,
   so some form of credential must travel in the connection URL.
   Passing the 15-minute access token directly risks it being logged by
   intermediate proxies/nginx access logs. Instead: an authenticated
   REST endpoint `POST /api/auth/ws-ticket/` issues a short-lived
   (~20s), single-use ticket stored in Redis (`SETEX ws_ticket:{ticket}
   20 {user_id}`); the WS handshake carries only this ticket
   (`/ws/tasktracker/?ticket=...`), and Channels middleware
   atomically reads-and-deletes it (GETDEL, or GET+DEL as fallback) to
   resolve the user and enforce one-time use.

**Alternatives considered:**
- Raw access token in query string — simplest, rejected due to
  proxy/access-log exposure risk.
- Per-project channel groups — rejected due to nullable `Task.project`
  requiring special-case handling for project-less tasks.
- Unfiltered broadcast + client-side filtering — rejected as an RBAC
  leak.

**Consequences:**
- Redis is now a required dependency for TaskTracker (previously
  Postgres-only) — used for both the Channels layer AND ws-ticket
  storage.
- Requires an ASGI-capable process (daphne/uvicorn) running alongside
  the existing gunicorn/WSGI process — deploy/nginx-routing changes are
  tracked as a separate phase (see AGENTS.md Phase 3 candidates: nginx
  reverse proxy), not bundled into this ADR.
- Task write paths (`TaskWriteSerializer.create`/`update`) gain an
  explicit call to broadcast the event after `.save()` — a deliberate
  choice over a `post_save` signal, to keep the side effect visible at
  the call site rather than an implicit signal handler (see
  AGENTS.md's "no business logic in views" — this extends the same
  preference for explicitness to signals).
- Computing "who can see this task" on every write is an extra query
  cost (iterates AccessRule/UserRole) — acceptable at this project's
  scale; would need revisiting (e.g. caching accessible-user-sets per
  role) if user count grew significantly.

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
