# Feature 21: Lazy LLM Initialization & WebSocket Exponential Backoff

## Lazy LLM Init
- `workflow.py` no longer instantiates `ChatOllama` at import time.
- `get_llm()` and `get_overseer_llm()` create the instance on first call.
- Prevents crashes if Ollama isn't running when the module is imported.

## WebSocket Exponential Backoff
- All 4 WebSocket connections in `app.js` (notifications, chat, debug, logs, LLM stream) use exponential backoff.
- Starts at 1s, doubles each failure, caps at 30s, adds random jitter.
- Resets to 1s on successful connection (`onopen`).
- Prevents connection storms during server restarts.
