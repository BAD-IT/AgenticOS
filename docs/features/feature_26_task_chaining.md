# Feature 26: Task Chaining & Pipelines

## Schema Foundation
- `parent_task_id` column added to `system_tasks` (nullable VARCHAR).
- `POST /api/v1/tasks/submit` accepts optional `parent_task_id` query param.
- Enables building dependency graphs between tasks.

## Current State
- Schema and API are ready. The worker does not yet auto-trigger child tasks.
- This is the foundation layer — full pipeline orchestration will be built on top.

## Future
- Worker checks for child tasks after completion and auto-submits them.
- Pipeline DAG visualization in the UI.
- Conditional branching based on parent task output.
