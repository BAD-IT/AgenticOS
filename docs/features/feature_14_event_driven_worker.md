# Feature 14: Event-Driven Worker via PostgreSQL LISTEN/NOTIFY

## Problem
The worker in `worker.py` uses `while True` + `asyncio.sleep(2)` to poll for new tasks. This adds 0–2 seconds latency to every task and wastes CPU cycles during idle periods. PostgreSQL `pg_notify` triggers already exist on `system_tasks` (firing on INSERT/UPDATE), but the worker doesn't listen to them.

## Goal
Replace blind polling with PostgreSQL `LISTEN/NOTIFY` so the worker wakes up instantly when a new task is inserted, while maintaining a fallback poll interval for resilience.

## Specifications

### 1. Worker LISTEN Loop (`worker.py`)
- After creating the pool, acquire a dedicated connection for `LISTEN`.
- Register a listener on `system_tasks_channel` using `asyncpg`'s `add_listener()`.
- When a notification fires, set an `asyncio.Event` to wake the worker immediately.
- The main loop uses `asyncio.wait_for(event.wait(), timeout=30)` instead of `asyncio.sleep(2)`:
  - If the event fires → process immediately (near-zero latency).
  - If timeout → fallback poll (resilience against missed notifications).

### 2. Notification Payload Safety (`init.sql`)
- PostgreSQL NOTIFY has an **8KB payload limit**. The current trigger sends `row_to_json(NEW)::text` which will silently fail for large payloads.
- Change the trigger to send only the `message_id`:
  ```sql
  PERFORM pg_notify('system_tasks_channel', NEW.message_id);
  ```
- WebSocket handlers that consume this channel must be updated to fetch the full row by ID if they need payload data.

### 3. WebSocket Compatibility (`websockets.py`)
- The `stream_chat` WebSocket currently receives full `row_to_json` payloads from `system_tasks_channel`.
- After the trigger change, it will receive only `message_id`. Update the handler to fetch the full row from the pool when a notification arrives.

### 4. Config Addition (`config.py`)
- Add `WORKER_FALLBACK_POLL_SECONDS` (default: `30`) for the fallback timeout.

## Acceptance Criteria
- Task submission to processing latency drops from 0–2s to <100ms.
- Worker CPU usage at idle drops to near-zero (no busy polling).
- If LISTEN connection drops, the worker falls back to 30-second polling without crashing.
- WebSocket clients continue to receive real-time task updates after the trigger payload change.
