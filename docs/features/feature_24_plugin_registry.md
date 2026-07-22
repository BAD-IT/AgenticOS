# Feature 24: Plugin/Tool Registry

## Implementation (`src/tools/registry.py`)
- `ToolRegistry` class with `register()`, `unregister()`, `get()`, `list_tools()`, `bulk_register()`.
- Global singleton `tool_registry` auto-populated from `TOOLS_MAP` at import.
- `GET /api/v1/tools` endpoint returns all registered tool names.

## Usage
```python
from src.tools.registry import tool_registry
tool_registry.register("my_custom_tool", my_tool_fn)
```

## Future
- Dynamic tool loading from a config file or database.
- Per-workspace tool permissions.
- Tool usage analytics.
