# API Reference — TaskTracker

> Update this file every time you add or change an endpoint.

Base URL: `http://localhost:8000/api/`

Auth header (all protected routes): `Authorization: Bearer <access_token>`

---

## Auth (`/api/auth/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register/` | public | Register new user |
| POST | `/auth/login/` | public | Login, returns JWT pair |
| POST | `/auth/logout/` | bearer | Blacklist refresh token |
| POST | `/auth/refresh/` | public | Get new access token |

---

## Users (`/api/users/`)

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| GET | `/users/me/` | bearer | any authenticated | Get own profile |
| PATCH | `/users/me/` | bearer | any authenticated | Update own profile |
| DELETE | `/users/me/` | bearer | any authenticated | Soft-delete own account |
| GET | `/users/` | bearer | user:read | List users (admin/manager) |
| GET | `/users/{id}/` | bearer | user:read | Get user detail |
| GET | `/users/{id}/roles/` | bearer | role:manage | List user's roles |
| POST | `/users/{id}/roles/` | bearer | role:manage | Assign role to user |
| DELETE | `/users/{id}/roles/{role_id}/` | bearer | role:manage | Remove role from user |

---

## RBAC (`/api/rbac/`)

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| GET | `/rbac/roles/` | bearer | role:manage | List roles |
| POST | `/rbac/roles/` | bearer | role:manage | Create role |
| GET | `/rbac/roles/{id}/` | bearer | role:manage | Role detail |
| PATCH | `/rbac/roles/{id}/` | bearer | role:manage | Update role |
| DELETE | `/rbac/roles/{id}/` | bearer | role:manage | Delete role |
| GET | `/rbac/permissions/` | bearer | permission:manage | List permissions |
| POST | `/rbac/permissions/` | bearer | permission:manage | Create permission |
| POST | `/rbac/roles/{id}/permissions/` | bearer | role:manage | Add perm to role |
| DELETE | `/rbac/roles/{id}/permissions/{perm_id}/` | bearer | role:manage | Remove perm from role |

---

## Tasks (`/api/tasks/`) — Phase 1: Mock

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| GET | `/tasks/` | bearer | task:read | Returns mock task list |
| POST | `/tasks/` | bearer | task:create | Returns mock created task |

---

## Projects (`/api/projects/`) — Phase 1: Mock

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| GET | `/projects/` | bearer | project:read | Returns mock project list |
| POST | `/projects/` | bearer | project:create | Returns mock created project |

---

## Error Responses

```json
// 401
{"error": "Authentication required", "detail": "No valid token provided"}

// 403
{"error": "Permission denied", "detail": "Required permission: task:read"}

// 400
{"error": "Validation error", "detail": {"email": ["This field is required."]}}
```
