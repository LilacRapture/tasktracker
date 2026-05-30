# API Reference — TaskTracker

> Update this file every time you add or change an endpoint.
> RBAC column values are `resource` / `action` as checked by `check_access()` — see `docs/rbac-schema.md`.

Base URL: `http://localhost:8000/api/`

Auth header (all protected routes): `Authorization: Bearer <access_token>`

---

## Auth (`/api/auth/`)

| Method | Endpoint | Auth | RBAC | Description |
|--------|----------|------|------|-------------|
| POST | `/auth/register/` | public | — | Register new user |
| POST | `/auth/login/` | public | — | Login, returns JWT pair |
| POST | `/auth/logout/` | bearer | — | Blacklist refresh token |
| POST | `/auth/refresh/` | public | — | Get new access token |

---

## Users (`/api/users/`)

| Method | Endpoint | Auth | RBAC | Description |
|--------|----------|------|------|-------------|
| GET | `/users/me/` | bearer | — | Get own profile (any authenticated user) |
| PATCH | `/users/me/` | bearer | — | Update own profile |
| DELETE | `/users/me/` | bearer | — | Soft-delete own account |
| GET | `/users/` | bearer | `user` / `read` | List users (needs `can_read_all` on `user`) |
| GET | `/users/{id}/` | bearer | `user` / `read` | Get user detail |
| GET | `/users/{id}/roles/` | bearer | `role` / `read` | List user's roles |
| POST | `/users/{id}/roles/` | bearer | `role` / `create` | Assign role to user |
| DELETE | `/users/{id}/roles/{role_id}/` | bearer | `role` / `delete` | Remove role from user |

> **Implementation note (UserRole assignment):** `POST` and `DELETE` on `/users/{id}/roles/` create or remove a **UserRole** join row, not a Role entity. The RBAC column uses `role` / `create` and `role` / `delete` because those endpoints are gated by AccessRule flags on the `role` resource. When implementing, consider a dedicated service (e.g. `assign_user_role()`) so the check stays explicit and is not confused with creating a Role record.

---

## RBAC (`/api/rbac/`)

Requires appropriate flags on the `role` or `access_rule` resource (typically admin). See `docs/rbac-schema.md` for admin endpoints.

| Method | Endpoint | Auth | RBAC | Description |
|--------|----------|------|------|-------------|
| GET | `/rbac/roles/` | bearer | `role` / `read` | List roles |
| POST | `/rbac/roles/` | bearer | `role` / `create` | Create role |
| GET | `/rbac/roles/{id}/` | bearer | `role` / `read` | Role detail |
| PATCH | `/rbac/roles/{id}/` | bearer | `role` / `update` | Update role |
| DELETE | `/rbac/roles/{id}/` | bearer | `role` / `delete` | Delete role |
| GET | `/rbac/roles/{id}/rules/` | bearer | `access_rule` / `read` | List access rules for role |
| POST | `/rbac/roles/{id}/rules/` | bearer | `access_rule` / `create` | Create access rule for a resource |
| PATCH | `/rbac/roles/{id}/rules/{resource}/` | bearer | `access_rule` / `update` | Update rule booleans for resource |
| DELETE | `/rbac/roles/{id}/rules/{resource}/` | bearer | `access_rule` / `delete` | Remove rule for resource |

---

## Tasks (`/api/tasks/`) — Phase 1: Mock

| Method | Endpoint | Auth | RBAC | Description |
|--------|----------|------|------|-------------|
| GET | `/tasks/` | bearer | `task` / `read` | Returns mock task list |
| POST | `/tasks/` | bearer | `task` / `create` | Returns mock created task |

---

## Projects (`/api/projects/`) — Phase 1: Mock

| Method | Endpoint | Auth | RBAC | Description |
|--------|----------|------|------|-------------|
| GET | `/projects/` | bearer | `project` / `read` | Returns mock project list |
| POST | `/projects/` | bearer | `project` / `create` | Returns mock created project |

---

## Error Responses

```json
// 401
{"error": "Authentication required", "detail": "No valid token provided"}

// 403
{"error": "Permission denied", "detail": "Required access: resource=task, action=read"}

// 400
{"error": "Validation error", "detail": {"email": ["This field is required."]}}
```
