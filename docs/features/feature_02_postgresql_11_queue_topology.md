# Feature 02: PostgreSQL 11-Queue Topology

Autonomous agents often suffer from "blocking loops" where the system freezes while waiting for a long-running LLM inference or code execution to finish. Agentic OS solves this by deeply decoupling the architecture using an asynchronous database state machine.

## 1. The Topology
During initialization (`init.sql`), the system creates a robust multi-queue topology in PostgreSQL:
1. `user_input_queue`: Raw messages from the frontend.
2. `tasks_queue`: Processed payloads ready for the LangGraph engine.
3. `error_queue`: Failed tasks awaiting triage.
4. `pending_queue`: Tasks that require long-running sandbox execution.
5. `notification_queue`: Messages to be streamed via WebSocket to the user.
6. `review_queue`: Tasks halted by the Constitution Node requiring human approval.
7. `result_output_queue`: Finalized artifacts ready to be delivered.
8. `agent_skills`: The vector embedding table used for Experience Consolidation.

## 2. Decoupled Processing
The FastAPI Orchestrator utilizes `asyncpg` to asynchronously read and write from these queues. When a user submits a task, it is immediately dropped into the `user_input_queue` and an HTTP 202 (Accepted) is returned. 

Background Python/Rust workers then poll these queues independently, picking up tasks, advancing their state, and moving them to the next logical queue without ever blocking the main UI ingress thread.
