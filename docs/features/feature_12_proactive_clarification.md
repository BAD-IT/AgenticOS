# Feature 12: Proactive Clarification & Resume Flow

## Problem
The Master Architecture Spec (M3 §4) defines a `REQUIRES_CLARIFICATION` anti-hallucination protocol, but it is not implemented. The LLM never detects missing parameters, never suspends a task, and if a task somehow reaches `REQUIRES_CLARIFICATION` status, there is no UI mechanism for the user to reply and resume the paused graph.

## Goal
Implement the full clarification lifecycle:
1. The LLM detects missing parameters and returns a structured clarification request.
2. The worker suspends the task at `REQUIRES_CLARIFICATION` and stores the question.
3. The UI displays the question and provides an input for the user to answer.
4. The user's reply injects the answer into the graph state and resumes execution.

## Specifications

### 1. Clarification Detection (`workflow.py` — `node_worker_thinking`)
- Update the system prompt to instruct the LLM: when critical parameters are missing (paths, URLs, names, credentials), do NOT guess. Instead, respond with a structured JSON block:
  ```
  <CLARIFICATION_NEEDED>{"question": "...", "missing_params": ["param1"]}</CLARIFICATION_NEEDED>
  ```
- After the LLM responds, check if the response content contains `<CLARIFICATION_NEEDED>`. If so, parse the question and return a state update that signals clarification is needed.

### 2. Worker Suspension (`worker.py`)
- After `_run_graph()` completes, inspect the final messages for a clarification marker.
- If found, update the task status to `REQUIRES_CLARIFICATION` and merge the question into the payload:
  ```sql
  UPDATE system_tasks SET status = 'REQUIRES_CLARIFICATION',
    payload = payload || '{"clarification_question": "..."}'::jsonb
  WHERE message_id = $1
  ```
- Do NOT mark the task as `RESULT_OUTPUT`. The task stays suspended.

### 3. Resume API Endpoint (`main.py`)
- Add `POST /api/v1/tasks/{message_id}/clarify` accepting `{"answer": "..."}`.
- The endpoint:
  1. Verifies the task is in `REQUIRES_CLARIFICATION` status.
  2. Merges the answer into the payload: `payload || '{"clarification_answer": "..."}'::jsonb`.
  3. Resets the status back to `USER_INPUT` so the worker picks it up again.
- When the worker picks it up, the existing chat history injection (Feature 11) ensures the LLM sees the original question and the user's answer in context.

### 4. UI Clarification Flow (`app.js`)
- The chat WebSocket handler already checks for `REQUIRES_CLARIFICATION` status and displays a message.
- Enhance: when a clarification message arrives, display the `clarification_question` text and show a dedicated inline reply input or prompt the user that their next message will answer the pending question.
- On submit, POST to `/api/v1/tasks/{message_id}/clarify` instead of creating a new task.

## Acceptance Criteria
- Sending "deploy the app" (intentionally vague) causes the agent to ask "Which port should the application run on?" instead of guessing.
- The user's reply resumes the original task with the injected parameter.
- The UI clearly shows the agent is waiting for clarification and provides a way to respond.
