# Feature 11: Short-Term Memory (Chat History Injection)

## Problem
`worker.py` starts every `GraphState` with `messages=[HumanMessage(content=task.intent)]`. The agent has zero conversation context — every task is processed in complete isolation. Even within the same workspace, the agent doesn't know what it did 30 seconds ago.

## Goal
Before invoking `app.astream()`, the worker must query `system_tasks` for the current `workspace_id` and inject prior conversation turns into `GraphState.messages`, giving the LLM full conversational context.

## Specifications

### 1. History Loading (`worker.py`)
- Before building the `state` dict, query the last N completed tasks for the current `workspace_id`:
  ```sql
  SELECT payload, status FROM system_tasks
  WHERE workspace_id = $1 AND status IN ('RESULT_OUTPUT', 'ERROR')
  ORDER BY created_at ASC
  ```
- Convert each row into a `HumanMessage` (from `payload.intent`) and `AIMessage` (from `payload.response`) pair.
- Append the current task's `HumanMessage` as the final message.
- Cap history to a configurable window (e.g., `CHAT_HISTORY_LIMIT=20` in `config.py`) to prevent token overflow.

### 2. Config Addition (`config.py`)
- Add `CHAT_HISTORY_LIMIT` environment variable (default: `20`).

### 3. Constraints
- Only inject messages from `RESULT_OUTPUT` and `ERROR` tasks (completed conversations).
- Skip the current task itself to avoid duplication.
- If no history exists (first message in workspace), behavior is unchanged.

## Acceptance Criteria
- Submitting "what did I just ask you?" as a second task in the same workspace returns a contextual answer referencing the first task.
- History is scoped per workspace — workspace 2 does not see workspace 1's messages.
- The agent operates identically to before when no prior history exists.
