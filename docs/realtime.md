# Realtime (WebSocket) — TaskTracker

> Canonical realtime spec. See ADR-014 (transport/protocol design) and
> ADR-015 (broadcast recipient computation) in `docs/decisions.md` for
> the reasoning behind these choices.

## Transport

Single WebSocket endpoint: `/ws/tasktracker/`

All messages — in both directions — use a versioned envelope:

```json
{"v": 1, "type": "task.updated", "payload": {...}}
```

## Event Types

| Type | Direction | Status |
|------|-----------|--------|
| `echo` | server → client | Phase 1 placeholder, will be removed once real events land |
| `task.created` | server → client | Implemented |
| `task.updated` | server → client | Implemented |
| `task.deleted` | server → client | Implemented |
| `presence.joined` | server → client | Implemented |
| `presence.left` | server → client | Implemented |
| `presence.editing_started` | client → server | Implemented |
| `presence.editing_stopped` | client → server | Implemented |

## Presence Details

**Self-echo suppression (`user_joined`/`user_left`):** `group_send` fans
out to every member of `PRESENCE_GROUP`, including the connection that
just triggered the event — without suppression, a client would receive
its own `presence.joined`/`presence.left`. `TaskTrackerConsumer.broadcast_event`
checks an optional `sender_channel` key on the group-send payload against
`self.channel_name` and skips delivery when they match. `broadcaster.py`'s
task/editing broadcasts never set `sender_channel`, so this only affects
the two presence lifecycle events — they're the only ones sent to a
group the sender is also a member of.

**RBAC scoping (`editing_started`/`editing_stopped`):** unlike
`joined`/`left` (sent to everyone in `PRESENCE_GROUP` unscoped — see
Channel Groups above), editing events reveal which specific task is
being worked on, which is task-level content. They reuse
`_users_with_task_access` (the same recipient computation as
`broadcast_task_event`, see ADR-015) via
`broadcast_presence_editing_event` — a user who can't read the task
never learns it's being edited, regardless of whether they're connected
and listening on `PRESENCE_GROUP`.

## Authentication

WebSocket connections cannot send custom headers, so a short-lived,
single-use ticket travels in the connection URL instead of the raw JWT
access token (avoids the token being logged by intermediate proxies).

1. Client calls `POST /api/auth/ws-ticket/` (normal Bearer-authenticated
   REST call) → receives `{"ticket": "..."}`
2. Client connects to `/ws/tasktracker/?ticket=<ticket>`
3. `TicketAuthMiddleware` (`apps/realtime/middleware.py`) reads the
   ticket from Redis, resolves it to a user, deletes it (one-time use),
   and rejects the connection (close code 4001) if missing/invalid/expired
4. Ticket TTL: 20 seconds — long enough for the client to open the
   connection right after issuance, short enough to limit exposure if
   logged anywhere unexpected

**Status:** Implemented (`apps/auth_core/views.py::WsTicketView`).

## Channel Groups

Per-user groups (`user_{id}`), not per-project. On every task
create/update/delete, the backend computes which users can currently
read that task (`apps/realtime/broadcaster._users_with_task_access`)
and sends the event to each of their personal groups individually.

Rejected per-project groups because `Task.project` is nullable
(`SET_NULL`), which would need special-case handling for project-less
tasks. Rejected unfiltered broadcast + client-side filtering as an RBAC
leak — see ADR-014.

## Recipient Computation Performance Note

`_users_with_task_access` deliberately duplicates `check_access()`'s
read-access precedence (`can_read_all` OR (own AND `can_read`)) as two
direct queries, rather than iterating every user and calling
`check_access()` per user. See ADR-015 for the full tradeoff — if
`docs/rbac-schema.md`'s access model changes, both places need updating.

## Consumer Reference

`apps/realtime/consumers.py` — `TaskTrackerConsumer`
`apps/realtime/middleware.py` — `TicketAuthMiddleware`
`apps/realtime/broadcaster.py` — `broadcast_task_event`, `_users_with_task_access`