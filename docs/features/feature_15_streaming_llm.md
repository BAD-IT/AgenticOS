# Feature 15: Streaming LLM Response to Chat UI

## Implementation
- `workflow.py` `node_worker_thinking` uses `get_llm().stream()` instead of `.invoke()`.
- Each token is broadcast via `pg_notify('llm_stream_channel', ...)`.
- New WebSocket endpoint `GET /api/v1/stream/llm` in `websockets.py` listens on that channel.
- UI (`app.js`) connects a streaming socket, appends tokens to a temporary chat message element.
- When the final task status arrives via the chat socket, the streaming element is finalized.

## Config
- No new config — uses existing `LLM_MODEL` and `OLLAMA_API_BASE`.
