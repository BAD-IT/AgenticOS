# Feature 16: Diagnostics Worker & Idle Daemon Activation

## Diagnostics Triage
- `idle_daemon.py` queries ERROR tasks missing `error_category` in payload.
- Calls `triage_fatal_error()` to classify as Category A/B/C.
- Merges the category back into the task payload for visibility.

## Idle Daemon Scheduler
- `run_idle_daemon()` is an async loop launched as a background task in `worker.py`.
- Every 60 seconds: checks queue counts, runs GC + VRAM flush when idle.
- Debug trace TTL: purges traces older than `DEBUG_TRACE_TTL_DAYS` (default 7).

## Experience Consolidation (Real LLM)
- `generate_skill_from_task()` now uses `ChatOllama` to analyze the task trajectory.
- LLM extracts a reusable methodology (max 150 words) instead of a static template string.
- Falls back to the original template if the LLM is unreachable.
