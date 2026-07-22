"""
Plugin/Tool Registry: Dynamically loads tools from the TOOLS_MAP and allows
runtime registration of additional tools without code changes.

Usage:
    from src.tools.registry import ToolRegistry
    registry = ToolRegistry()
    registry.register("my_tool", my_tool_function)
    tool_fn = registry.get("my_tool")
    all_tools = registry.list_tools()
"""
import logging
from typing import Dict, Callable, Any, List

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all available agent tools."""

    def __init__(self):
        self._tools: Dict[str, Any] = {}

    def register(self, name: str, tool_fn: Any) -> None:
        """Register a tool by name. Overwrites if already registered."""
        self._tools[name] = tool_fn
        logger.info(f"ToolRegistry: Registered tool '{name}'")

    def unregister(self, name: str) -> bool:
        """Remove a tool from the registry. Returns True if it existed."""
        if name in self._tools:
            del self._tools[name]
            logger.info(f"ToolRegistry: Unregistered tool '{name}'")
            return True
        return False

    def get(self, name: str) -> Any:
        """Retrieve a tool by name, or None if not found."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """Return a sorted list of registered tool names."""
        return sorted(self._tools.keys())

    def all(self) -> Dict[str, Any]:
        """Return the full tools dict (read-only copy)."""
        return dict(self._tools)

    def bulk_register(self, tools_map: Dict[str, Any]) -> None:
        """Register multiple tools at once from a dict."""
        for name, fn in tools_map.items():
            self.register(name, fn)


# Global singleton
tool_registry = ToolRegistry()
