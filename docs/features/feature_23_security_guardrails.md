# Feature 23: Semantic Security Guardrails

## Implementation
- `check_security_guardrails()` in `main.py` scans task intent against blocked patterns.
- Blocked patterns include prompt injection attempts, SQL injection markers, and social engineering phrases.
- Returns HTTP 422 with a clear rejection reason if a pattern matches.

## Blocked Patterns
- `ignore previous instructions`, `ignore all instructions`
- `system prompt`, `reveal your prompt`, `bypass security`
- `DROP TABLE`, `DELETE FROM`, `; --`, `' OR 1=1`

## Design
- Pattern list is extensible — add new entries to `BLOCKED_PATTERNS`.
- Case-insensitive matching.
- Applied before the task reaches the database or the LLM.
