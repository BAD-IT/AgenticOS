# Feature 17: Task Cancellation & Priorities

## Task Priorities
- New `task_priority` enum in `init.sql`: `URGENT`, `NORMAL`, `LOW`.
- `system_tasks` table gets a `priority` column (default `NORMAL`).
- Worker picks tasks ordered by `priority ASC, created_at ASC` (URGENT first).
- `POST /api/v1/tasks/submit` accepts `priority` query param.

## Task Cancellation
- `POST /api/v1/tasks/{message_id}/cancel` endpoint.
- Validates task isn't already finished, then marks as ERROR with "cancelled by user" message.

## Schema Changes
- `parent_task_id` column added for future task chaining.
- `webhook_url` column added for outbound webhook delivery.
- Index on `(priority, status, created_at)` for efficient priority ordering.
