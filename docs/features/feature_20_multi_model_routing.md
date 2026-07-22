# Feature 20: Multi-Model Routing

## Implementation
- `get_llm()` returns the primary model (with tools) for `Node_Worker_Thinking`.
- `get_overseer_llm()` returns a separate model (no tools) for `Node_Review`.
- Overseer uses `REVIEW_MODEL` if set, else falls back to `LLM_MODEL`.

## Config
- `REVIEW_MODEL` environment variable (default: empty = use `LLM_MODEL`).

## Use Cases
- Use a fast/cheap model for Overseer review (e.g., `gemma3:4b`).
- Use a heavy reasoning model for the main worker (e.g., `gemma4:12b`).
- Future: route by task complexity, cost, latency requirements.
