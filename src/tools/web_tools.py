import os
import re
import subprocess
from pathlib import Path
from langchain_core.tools import tool
from src.core.config import settings

WORKSPACE_INBOX = Path(settings.INBOX_DIR).resolve()
WORKSPACE_OUTBOX = Path(settings.OUTBOX_DIR).resolve()


@tool
def web_fetch(url: str) -> str:
    """Fetches the text content of a URL. Use for reading web pages, APIs, or downloading data."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "AgenticOS/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            # Truncate to avoid overwhelming the LLM context
            if len(content) > 8000:
                content = content[:8000] + "\n... [truncated]"
            return content
    except Exception as e:
        return f"Error fetching URL: {e}"


@tool
def grep_workspace(pattern: str, directory: str = "outbox") -> str:
    """Searches for a text pattern in workspace files. directory must be 'inbox' or 'outbox'."""
    base = WORKSPACE_OUTBOX if directory == "outbox" else WORKSPACE_INBOX
    if not base.exists():
        return f"Error: Directory {directory} does not exist."
    
    matches = []
    try:
        for fpath in base.rglob("*"):
            if fpath.is_file() and not fpath.name.startswith("."):
                try:
                    text = fpath.read_text(errors="replace")
                    for i, line in enumerate(text.splitlines(), 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            rel = fpath.relative_to(base)
                            matches.append(f"{rel}:{i}: {line.strip()}")
                            if len(matches) >= 50:
                                matches.append("... [results capped at 50]")
                                return "\n".join(matches)
                except Exception:
                    pass
    except Exception as e:
        return f"Error searching: {e}"
    
    return "\n".join(matches) if matches else "No matches found."


@tool
def http_request(url: str, method: str = "GET", body: str = "", headers: str = "") -> str:
    """Makes an HTTP request. method: GET/POST/PUT/DELETE. headers: JSON string of headers. body: request body for POST/PUT."""
    try:
        import urllib.request
        import json
        
        req_headers = {"User-Agent": "AgenticOS/1.0", "Content-Type": "application/json"}
        if headers:
            try:
                req_headers.update(json.loads(headers))
            except json.JSONDecodeError:
                return "Error: headers must be valid JSON string"
        
        data = body.encode("utf-8") if body and method.upper() in ("POST", "PUT") else None
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8", errors="replace")
            status = resp.status
            if len(resp_body) > 5000:
                resp_body = resp_body[:5000] + "\n... [truncated]"
            return f"HTTP {status}\n{resp_body}"
    except Exception as e:
        return f"HTTP request failed: {e}"
