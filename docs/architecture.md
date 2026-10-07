# Architecture Overview — TaskTracker

## System Purpose

API-only backend with:
1. Stateless JWT authentication
2. Custom ownership-aware RBAC with its own DB schema
3. Task and project management as the business domain
4. Realtime task events and presence over WebSocket

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 (pinned, see ADR-006) |
| Framework | Django 5 + Django REST Framework |
| Auth | djangorestframework-simplejwt |
| Database | PostgreSQL 16 |
| Realtime | Django Channels + daphne (ASGI), Redis 7 (channel layer, WS tickets, cache) |
| HTTP serving | gunicorn (WSGI) + whitenoise for static files |
| Edge | nginx reverse proxy, django-cors-headers |
| Config | python-decouple (`.env`) |
| API docs | drf-spectacular |
| Tests | pytest, pytest-django, pytest-asyncio |

## Runtime Topology

```
client ──► nginx ──┬── /ws/  ──► web_ws (daphne, ASGI)
                   └── /     ──► web    (gunicorn, WSGI)

web, web_ws ──► PostgreSQL
web, web_ws ──► Redis
```

Decisions: ADR-013 (Docker deploy), ADR-017 (nginx + CORS).

## Project Layout

```
config/            settings, root urls, wsgi/asgi
apps/
  users/           custom User model, profile endpoints
  auth_core/       register, login, logout, refresh, WS ticket
  rbac/            Role / AccessRule / UserRole, enforcement, admin API
  tasks/           Task domain
  projects/        Project domain
  realtime/        WS consumer, ticket middleware, broadcasts
  common/          shared DRF helpers
docs/              architecture, api, rbac-schema, realtime, decisions
nginx/             reverse proxy config
conftest.py        shared pytest fixtures
```

App responsibilities and rules: `AGENTS.md`.

## Request Lifecycle

```
HTTP request
  → config/urls.py → app urls.py → DRF view
      ├── IsAuthenticated (SimpleJWT) ........ 401
      ├── RBACPermission
      │     ├── has_permission: endpoint gate .. 403
      │     └── has_object_permission: detail views, ownership-aware .. 403
      └── serializer → response
```

List views also narrow rows with `get_accessible_queryset()`. Details and the full algorithm: `docs/rbac-schema.md`.

Views declare what they require:

```python
rbac_resource = "task"
rbac_action = "auto"   # derived from the HTTP method; or an explicit action
```

## Authentication

Short-lived access token + refresh token; logout blacklists the refresh token. Django sessions are used for `/admin/` only (ADR-002). Endpoint shapes: `docs/api.md`. WebSocket handshake auth: `docs/realtime.md`.

## Data Stores

**PostgreSQL**
- Users: `users_user`
- RBAC: `rbac_role`, `rbac_accessrule`, `rbac_userrole` (fields: `docs/rbac-schema.md`)
- Business: `tasks_task`, `projects_project`

**Redis** (no Postgres tables)
- Channels layer (pub/sub)
- One-time WS tickets (`ws_ticket:{ticket}`, short TTL)