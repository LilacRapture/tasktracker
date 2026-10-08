# Realtime (WebSocket) — TaskTracker

> Canonical realtime spec. Rationale: ADR-014 (transport, groups, auth), ADR-015 (recipients), ADR-016 (presence). Code: `apps/realtime/`.

## Transport

One endpoint, `/ws/tasktracker/`. Every message, in both directions, is a versioned envelope:

```json
{"v": 1, "type": "task.updated", "payload": {...}}
```

## Events

| Type | Direction | Payload | Delivered to |
|------|-----------|---------|--------------|
| `task.created`, `task.updated`, `task.deleted` | server → client | `id`, `title`, `status`, `owner_id`, `project_id` | users who can read the task |
| `presence.joined`, `presence.left` | server → client | `user_id`, `email` | every other connected user |
| `presence.editing_started`, `presence.editing_stopped` | client → server | `task_id` | — |
| `presence.editing_started`, `presence.editing_stopped` | server → client | `task_id`, `user_id`, `email` | users who can read the task |
| `echo` | server → client | the received message | the sender; connectivity-check placeholder, to be removed |

- "Can read the task" is the REST rule: `can_read_all`, or `can_read` on own tasks.
- `presence.joined` / `presence.left` are unscoped (bare presence isn't task content) and never echo back to the connection that caused them.
- An editing event for a missing or unreadable task is dropped silently.

## Authentication

Browsers can't send an `Authorization` header on a WebSocket, so the handshake carries a one-time ticket instead of the access token.

1. `POST /api/auth/ws-ticket/` (Bearer) → `{"ticket": "..."}`
2. Connect to `/ws/tasktracker/?ticket=<ticket>`

The ticket is single-use with a 20 s TTL. A missing, invalid, or expired ticket gets the connection rejected.