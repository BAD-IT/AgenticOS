# Feature 19: Expanded Tool Inventory

## New Tools (`src/tools/web_tools.py`)

### `web_fetch(url: str) -> str`
- Fetches text content from a URL. Truncated to 8000 chars.
- Useful for reading web pages, APIs, documentation.

### `grep_workspace(pattern: str, directory: str) -> str`
- Regex search across workspace files (inbox or outbox).
- Returns `file:line: content` format, capped at 50 matches.

### `http_request(url, method, body, headers) -> str`
- Full HTTP client supporting GET/POST/PUT/DELETE.
- Headers as JSON string. Returns status code + response body.

## Registration
- All tools registered in `TOOLS_MAP` and the global `ToolRegistry`.
- LLM sees all tools via `.bind_tools()`.
