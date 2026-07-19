# Feature 02: PostgreSQL Single-Table Topology

Autonomous agents often suffer from "blocking loops" where the system freezes while waiting for a long-running LLM inference or code execution to finish. Agentic OS solves this by deeply decoupling the architecture using an asynchronous database state machine.

## 1. The Single-Table Topology
Originally utilizing 7 different queues, the system has been refactored for massive Disk I/O efficiency into a Single-Table Topology via `init.sql`:
- **`system_tasks`**: A single table housing all active workflows.
- **`task_status` ENUM**: `USER_INPUT`, `TASK`, `PENDING`, `REVIEW`, `RESULT_OUTPUT`, `ERROR`.

## 2. Decoupled Processing
The FastAPI Orchestrator utilizes `asyncpg` to asynchronously interface with this table. When a user submits a task, an `INSERT` adds it to `system_tasks` with the `USER_INPUT` status, returning an HTTP 202. Background workers atomicly pick up tasks using `SELECT ... FOR UPDATE SKIP LOCKED` and simply update the ENUM state, completely eliminating cross-table thrashing.
