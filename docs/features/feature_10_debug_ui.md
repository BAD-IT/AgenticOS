# Feature 10: System Transparency & Debug Interface

## Overview
The Debug Interface provides real-time visibility into the LangGraph cognitive engine, allowing developers to inspect every node execution, state diff, and task lifecycle transition as it happens.

## Components

### Left Panel — Live Cognitive Trace (`#cognitive-trace-feed`)
- Streams node execution events via WebSocket (`/api/v1/stream/debug`).
- Color-coded labels: `[THINKING]` (amber), `[TOOL EXEC]` (blue), `[REVIEW]` (purple), `[RESULT]` (green).
- **Task separators**: A horizontal rule with the short task ID is inserted whenever a new task begins, making it easy to distinguish execution boundaries.

### Debug Tab — Full State Trace (`#debug-feed`)
- Chronological list of every node execution with full `state_diff` JSON payloads.
- REST-fetched on tab switch (`GET /api/v1/debug/traces/:workspace`) and live-updated via WebSocket.
- Same task-boundary separators as the left panel for visual consistency.

### Chat Loading Indicator
- Animated dot-pulse indicator shown while the worker is processing a task.
- Text dynamically updates with telemetry category/message from the notification WebSocket.
- Hides only when the task reaches a terminal status (`RESULT_OUTPUT`, `ERROR`, `REQUIRES_CLARIFICATION`), preventing premature dismissal on the initial `USER_INPUT` notification.

### Telemetry Tab — Queue Counters
- Live queue depth counters grouped by lifecycle stage: Ingestion, Processing, Validation, Output, Errors.
- Error counter container auto-hides when error count is zero.

## Data Flow
1. Worker inserts rows into `system_debug_trace` table per node execution.
2. PostgreSQL `NOTIFY system_debug_channel` trigger fires on each insert.
3. Orchestrator WebSocket endpoint relays the notification JSON to all connected browser clients.
4. Browser renders trace items and separators in both left panel and debug tab feeds.

## Configuration
- `TASK_TIMEOUT_SECONDS` (default `60`): Maximum time a task may execute before the worker marks it `ERROR` and surfaces the timeout message in the Chat UI.
