# RBAC Schema — TaskTracker

> **Canonical RBAC spec.** All other docs (`AGENTS.md`, `architecture.md`, `api.md`, ADRs) follow this file.
> Implement models, `check_access()`, `RBACPermission`, and seed data exactly as described here.

## Core Idea

Access control is **ownership-aware**: some actions apply only to objects
the user created themselves (`owner_id = user.id`), others apply to all objects
regardless of ownership.

Three tables drive the system:

```
User ──has──► UserRole ──► Role ──has──► AccessRule
                                              │
                              resource: "task"│
                              can_read        │ ← read own
                              can_read_all    │ ← read anyone's
                              can_create      │
                              can_update      │ ← update own
                              can_update_all  │ ← update anyone's
                              can_delete      │ ← delete own
                              can_delete_all  │ ← delete anyone's
```

---

## Tables

### Role

Named group that bundles access rules.

| Field | Type | Notes |
|-------|------|-------|
| id | BigInt PK | auto |
| name | varchar(50) | unique — `admin`, `manager`, `developer`, `viewer` |
| description | text | human-readable |
| created_at | datetime | auto |

---

### UserRole

Which roles a user has. Many-to-many with audit fields.

| Field | Type | Notes |
|-------|------|-------|
| id | BigInt PK | |
| user_id | FK → User | |
| role_id | FK → Role | |
| assigned_at | datetime | auto |
| assigned_by_id | FK → User, nullable | who granted the role |

---

### AccessRule

One row = one role's access rules on one resource.
A role can have at most one `AccessRule` per resource (unique together).

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| id | BigInt PK | | |
| role_id | FK → Role | | |
| resource | varchar(50) | | `task`, `project`, `user`, `role`, `access_rule` |
| can_read | bool | False | read objects owned by self |
| can_read_all | bool | False | read any object of this resource |
| can_create | bool | False | create new objects |
| can_update | bool | False | update objects owned by self |
| can_update_all | bool | False | update any object of this resource |
| can_delete | bool | False | delete objects owned by self |
| can_delete_all | bool | False | delete any object of this resource |

**Unique constraint:** `(role_id, resource)` — one rule set per role per resource.

---

## Resources

| resource string | Covers |
|----------------|--------|
| `task` | Task objects |
| `project` | Project objects |
| `user` | User profiles (other users' data) |
| `role` | Role management |
| `access_rule` | AccessRule management (the RBAC rules themselves) |

---

## Seed Data

### Roles

| name | description |
|------|-------------|
| admin | Full access to everything including RBAC management |
| manager | Manage projects and all tasks within them |
| developer | Work on tasks; limited to own objects outside assigned projects |
| viewer | Read-only across tasks and projects |

### AccessRules per Role

**admin** — full access to everything:

| resource | read | read_all | create | update | update_all | delete | delete_all |
|----------|------|----------|--------|--------|------------|--------|------------|
| task | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| project | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| user | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| role | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| access_rule | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**manager** — full over tasks/projects, read users, no RBAC management:

| resource | read | read_all | create | update | update_all | delete | delete_all |
|----------|------|----------|--------|--------|------------|--------|------------|
| task | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| project | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| user | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| role | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| access_rule | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

**developer** — own tasks/projects, read others':

| resource | read | read_all | create | update | update_all | delete | delete_all |
|----------|------|----------|--------|--------|------------|--------|------------|
| task | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| project | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| user | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| role | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| access_rule | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

**viewer** — read-only, own objects only in terms of mutation (none):

| resource | read | read_all | create | update | update_all | delete | delete_all |
|----------|------|----------|--------|--------|------------|--------|------------|
| task | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| project | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| user | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| role | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| access_rule | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

---

## Access check algorithm (`check_access`)

Evaluates the caller's **AccessRule** rows for the requested `resource` and `action`.
Maps actions to boolean flags: `read` → `can_read` / `can_read_all`, etc.

```python
def check_access(
    user: User,
    resource: str,
    action: str,          # "read" | "create" | "update" | "delete"
    obj_owner_id: int | None = None,   # owner of the object being accessed
) -> bool:
    """
    Returns True if any of the user's roles grants the action on resource
    via AccessRule flags.

    For read/update/delete: checks can_{action}_all first, then can_{action}
    when obj_owner_id == user.id. create uses only can_create.
    """
    if not user.is_active:
        return False

    user_role_ids = UserRole.objects.filter(
        user=user
    ).values_list("role_id", flat=True)

    rules = AccessRule.objects.filter(
        role_id__in=user_role_ids,
        resource=resource,
    )

    if action == "create":
        return rules.filter(can_create=True).exists()

    all_field = f"can_{action}_all"   # e.g. "can_read_all"
    own_field  = f"can_{action}"      # e.g. "can_read"

    # Global access: can_{action}_all on this resource
    if rules.filter(**{all_field: True}).exists():
        return True

    # Own-object access: can_{action} when caller owns the object
    if obj_owner_id is not None and obj_owner_id == user.id:
        return rules.filter(**{own_field: True}).exists()

    return False
```

Wrap this in the DRF `RBACPermission` class in `apps/rbac/permissions.py`.

---

## Two-layer enforcement (list vs object level)

`check_access()` requires `obj_owner_id` to grant own-object access — it
answers "can this user act on THIS specific object?" That's correct for
detail views (GET/PATCH/DELETE on `/tasks/{id}/`).

For **list/create** endpoints there is no single object yet, so a second
function is used:

### `has_any_access(user, resource, action) -> bool`

Endpoint-level gate. Returns True if the user has `can_{action}` OR
`can_{action}_all` (for create: `can_create`). Used in
`RBACPermission.has_permission()`.

### `get_accessible_queryset(user, resource, action, queryset) -> QuerySet`

Row-level filter for list endpoints. Assumes the model has an `owner` FK.

- `can_{action}_all` → full queryset
- `can_{action}` only → `queryset.filter(owner=user)`
- neither → `queryset.none()`

### Summary table

| Endpoint type | Permission check | Row filtering |
|---|---|---|
| List (GET /tasks/) | `has_any_access` | `get_accessible_queryset` |
| Create (POST /tasks/) | `has_any_access` (can_create) | n/a |
| Detail (GET/PATCH/DELETE /tasks/{id}/) | `has_object_permission` → `check_access(obj_owner_id=...)` | n/a |

Both layers are required: `has_any_access` alone would let a
`can_read`-only user reach `/tasks/` but `get_accessible_queryset` then
correctly limits results to their own tasks.

---

## How Views Declare Required Access

```python
class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "task"
    rbac_action = "auto"   # GET→read, PATCH/PUT→update, DELETE→delete (via _method_to_action)

    def get_rbac_owner_id(self, request, obj):
        return obj.owner_id
```

---

## Self-Service Capabilities

`GET /api/users/me/capabilities/` — IsAuthenticated only, no
RBACPermission (mirrors `/users/me/`'s "read my own data" pattern, not
"read the role resource"). Returns the requesting user's role names
plus merged (OR'd across all assigned roles) AccessRule flags per
resource, via `apps.rbac.permissions.get_user_capabilities()`. Intended
for frontend clients to derive UI visibility without needing to know
role names or duplicate precedence logic — see the tasktracker-frontend
repo's AGENTS.md for how it's consumed.

---

## Admin API Endpoints

Only accessible to users with the required **AccessRule** flags on the `role` or `access_rule` resource:

```
# Roles
GET    /api/rbac/roles/
POST   /api/rbac/roles/
GET    /api/rbac/roles/{id}/
PATCH  /api/rbac/roles/{id}/
DELETE /api/rbac/roles/{id}/

# Access rules per role
GET    /api/rbac/roles/{id}/rules/
POST   /api/rbac/roles/{id}/rules/          — create rule for a resource
PATCH  /api/rbac/roles/{id}/rules/{res}/    — update booleans for resource
DELETE /api/rbac/roles/{id}/rules/{res}/    — remove rule entirely

# User role assignment
GET    /api/users/{id}/roles/
POST   /api/users/{id}/roles/
DELETE /api/users/{id}/roles/{role_id}/
```
