# RBAC Schema — TaskTracker

## Core Idea

Access control is **ownership-aware**: some permissions apply only to objects
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

One row = one role's permissions on one resource.
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

## Permission Check Algorithm

```python
def check_access(
    user: User,
    resource: str,
    action: str,          # "read" | "create" | "update" | "delete"
    obj_owner_id: int | None = None,   # owner of the object being accessed
) -> bool:
    """
    Returns True if user may perform action on resource.

    For read/update/delete: first checks the _all variant.
    If not, checks the plain variant only when obj_owner_id == user.id.
    create has no ownership concept — only can_create matters.
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

    # Has permission on ALL objects of this resource
    if rules.filter(**{all_field: True}).exists():
        return True

    # Has permission only on own objects
    if obj_owner_id is not None and obj_owner_id == user.id:
        return rules.filter(**{own_field: True}).exists()

    return False
```

This runs inside the custom DRF `RBACPermission` class in `apps/rbac/permissions.py`.

---

## How Views Declare Required Access

```python
class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated, RBACPermission]
    rbac_resource = "task"
    rbac_action = "update"   # RBACPermission will pass obj.owner_id automatically
```

---

## Admin API Endpoints

Only accessible to users whose role has `access_rule` resource permissions:

```
# Roles
GET    /api/rbac/roles/
POST   /api/rbac/roles/
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
