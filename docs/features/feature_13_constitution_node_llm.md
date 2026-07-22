# Feature 13: Constitution Node — Real LLM-Driven Strategy Analysis

## Problem
The Constitution Node (Overseer) in `node_review` returns a hardcoded static string:
```python
"<SYSTEM_OVERRIDE> Stop using the failing approach. Try browser automation instead."
```
This is context-blind — it tells the agent to "try browser automation" regardless of whether the task involves file I/O, API calls, or anything else. The entire macro-loop safety layer is non-functional against real-world failures.

## Goal
Replace the static override with an actual LLM call that:
1. Reads the recent failure history from the graph state.
2. Identifies the strategic flaw (e.g., wrong tool, wrong parameters, wrong approach).
3. Generates a contextual directive forcing the worker to pivot.

## Specifications

### 1. Overseer LLM Call (`workflow.py` — `node_review`)
- Use a separate LLM invocation with a strict "Constitution" system prompt:
  ```
  You are the Agentic OS Overseer. You do NOT solve the user's task.
  Your role is to analyze WHY the worker agent failed repeatedly and
  inject a mandatory strategic directive to break the failure loop.

  Analyze the failure history below. Identify the root cause.
  Output a single <SYSTEM_OVERRIDE> directive telling the worker
  what to STOP doing and what NEW approach to use instead.
  ```
- Feed the last N messages (containing tool failures and error traces) as context.
- The Overseer must NOT call tools — use a plain `ChatOllama` instance without `.bind_tools()`.

### 2. Model Selection
- Use the same `LLM_MODEL` for now (single-model mode).
- The architecture supports future multi-model routing (e.g., fast model for review, heavy model for reasoning) but that is out of scope here.

### 3. Error Budget Reset
- After the Constitution Node injects its directive, reset `tool_error_count` to 0 so the worker gets a fresh retry budget with the new strategy.
- Cap total Constitution Node invocations per task to 2 (configurable via `MAX_OVERSEER_RETRIES` in `config.py`). If the Overseer fires 2 times and the worker still fails, route the task to `ERROR` status instead of looping forever.

### 4. State Changes (`models.py`)
- Add `overseer_invocation_count: int` to `GraphState` to track how many times the Overseer has been called for this task.

## Acceptance Criteria
- When the worker fails 3 times on a file operation, the Overseer analyzes the specific errors and generates a contextual override (e.g., "The file path does not exist. Stop using read_file on /foo. Check the inbox directory first.").
- After 2 Overseer interventions without resolution, the task is routed to ERROR with a clear diagnostic.
- The override is injected as a `SystemMessage` visible in the debug trace.
