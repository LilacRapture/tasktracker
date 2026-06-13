# API Reference — TaskTracker

> Update this file every time you add or change an endpoint.
> RBAC column values are `resource` / `action` as checked by `check_access()` — see `docs/rbac-schema.md`.

Base URL: `http://localhost:8000/api/`

Auth header (all protected routes): `Authorization: Bearer <access_token>`

---

## Auth (`/api/auth/`)

| Method | Endpoint | Auth | RBAC | Description |
|--------|----------|------|------|-------------|
| POST | `/auth/register/` | public | — | Register; returns user + JWT pair (201) |
| POST | `/auth/login/` | public | — | Login; returns user + JWT pair (200) |
| POST | `/auth/logout/` | bearer | — | Blacklist refresh token (body: `{"refresh": "..."}`) |
| POST | `/auth/refresh/` | public | — | New access token (SimpleJWT; body: `{"refresh": "..."}`) |

**Register / login success (shape):**

```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Last First",
    "created_at": "2026-05-31T12:00:00Z"
  },
  "access": "<access_token>",
  "refresh": "<refresh_token>"
}
```

---

## Users (`/api/users/`)

| Method | Endpoint | Auth | RBAC | Description |
|--------|----------|------|------|-------------|
| GET | `/users/me/` | bearer | — | Get own profile (any authenticated user) |
| PATCH | `/users/me/` | bearer | — | Update own profile (`first_name`, `last_name`, `middle_name`) |
| DELETE | `/users/me/` | bearer | — | Soft-delete own account (`is_active=False`); optional `refresh` in body to blacklist |
| GET | `/users/` | bearer | `user` / `read` | List users (needs `can_read_all` on `user`) |
| GET | `/users/{id}/` | bearer | `user` / `read` | Get user detail |
| GET | `/users/{id}/roles/` | bearer | `role` / `read` | List user's roles |
| POST | `/users/{id}/roles/` | bearer | `role` / `create` | Assign role (`{"role_id": 1}`) |
| DELETE | `/users/{id}/roles/{role_id}/` | bearer | `role` / `delete` | Remove role from user |

> **UserRole assignment:** `POST` / `DELETE` on `/users/{id}/roles/` manage **UserRole** join rows, gated by AccessRule flags on the `role` resource. Implemented via `AssignRoleSerializer` and `UserRoleListView` / `UserRoleDetailView` in `apps/rbac/views.py`.

---

## RBAC (`/api/rbac/`)

Requires appropriate flags on the `role` or `access_rule` resource (typically admin). See `docs/rbac-schema.md` for admin endpoints.

| Method | Endpoint | Auth | RBAC | Description |
|--------|----------|------|------|-------------|
| GET | `/rbac/roles/` | bearer | `role` / `read` | List roles (includes nested `access_rules`) |
| POST | `/rbac/roles/` | bearer | `role` / `create` | Create role |
| GET | `/rbac/roles/{id}/` | bearer | `role` / `read` | Role detail |
| PATCH | `/rbac/roles/{id}/` | bearer | `role` / `update` | Update role |
| DELETE | `/rbac/roles/{id}/` | bearer | `role` / `delete` | Delete role |
| GET | `/rbac/roles/{id}/rules/` | bearer | `access_rule` / `read` | List access rules for role |
| POST | `/rbac/roles/{id}/rules/` | bearer | `access_rule` / `create` | Create access rule for a resource |
| PATCH | `/rbac/roles/{id}/rules/{resource}/` | bearer | `access_rule` / `update` | Update rule booleans for resource |
| DELETE | `/rbac/roles/{id}/rules/{resource}/` | bearer | `access_rule` / `delete` | Remove rule for resource |

---

## Tasks (`/api/tasks/`)

| Method | Endpoint | Auth | RBAC | Description |
|--------|----------|------|------|-------------|
| GET | `/tasks/` | bearer | `task` / `read` | List tasks (own or all, depending on `can_read_all`) |
| POST | `/tasks/` | bearer | `task` / `create` | Create task (`owner` = caller) |
| GET | `/tasks/{id}/` | bearer | `task` / `read` | Task detail |
| PATCH | `/tasks/{id}/` | bearer | `task` / `update` | Update task (own, or any with `can_update_all`) |
| DELETE | `/tasks/{id}/` | bearer | `task` / `delete` | Delete task (own, or any with `can_delete_all`) |

## Projects (`/api/projects/`)

| Method | Endpoint | Auth | RBAC | Description |
|--------|----------|------|------|-------------|
| GET | `/projects/` | bearer | `project` / `read` | List projects (own or all) |
| POST | `/projects/` | bearer | `project` / `create` | Create project (`owner` = caller) |
| GET | `/projects/{id}/` | bearer | `project` / `read` | Project detail |
| PATCH | `/projects/{id}/` | bearer | `project` / `update` | Update project |
| DELETE | `/projects/{id}/` | bearer | `project` / `delete` | Delete project |

---

## Error Responses

Phase 1 uses **DRF defaults** for most errors. Some RBAC write paths return a custom `{"error": "..."}` body — see below.

```json
// 401 — missing/invalid JWT (DRF/SimpleJWT default)
{"detail": "Authentication credentials were not provided."}

// 403 — RBACPermission denied (typical)
{"detail": "Permission denied. Required: task:read"}

// 403 — explicit check in some views (tasks, projects, rbac writes)
{"error": "Permission denied. Required: task:create"}

// 400 — serializer validation (DRF default)
{"email": ["This field is required."]}

// 400 — non-field validation
{"non_field_errors": ["Invalid email or password."]}
```

**Success messages (non-error):**

```json
// Logout
{"detail": "Successfully logged out."}

// Soft delete
{"detail": "Account deactivated successfully."}
```
