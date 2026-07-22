# Feature 18: API Key Authentication

## Implementation
- `APIKeyMiddleware` in `main.py` using Starlette's `BaseHTTPMiddleware`.
- Checks `X-API-Key` header or `api_key` query parameter against `AGENTICOS_API_KEY` env var.
- Returns 401 if key is missing or invalid.

## Bypass Rules
- Auth is **disabled** if `AGENTICOS_API_KEY` is empty (default — backward-compatible).
- Static files (`/ui/*`), root (`/`), OpenAPI docs, and WebSocket upgrades are exempt.

## Config
- `AGENTICOS_API_KEY` environment variable (default: empty = no auth).
