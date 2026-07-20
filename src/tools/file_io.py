import os
from pathlib import Path
from langchain_core.tools import tool
from src.core.config import settings

# Base paths (resolving to ensure secure checking)
WORKSPACE_INBOX = Path(settings.INBOX_DIR).resolve()
WORKSPACE_OUTBOX = Path(settings.OUTBOX_DIR).resolve()

def _is_safe_path(requested_path: Path, base_paths: list[Path]) -> bool:
    resolved_path = requested_path.resolve()
    for bp in base_paths:
        if resolved_path.is_relative_to(bp):
            return True
    return False

@tool
def read_file(filepath: str) -> str:
    """Reads a file from the sandbox."""
    target = Path(filepath)
    if not _is_safe_path(target, [WORKSPACE_INBOX, WORKSPACE_OUTBOX]):
        return f"Error: Access denied: {filepath} is outside the sandbox."
    try:
        with open(target, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def write_file(filepath: str, content: str) -> str:
    """Writes content to a file in the sandbox."""
    target = Path(filepath)
    if not _is_safe_path(target, [WORKSPACE_OUTBOX]):
        return f"Error: Access denied: Can only write to {WORKSPACE_OUTBOX}."
    
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'w') as f:
            f.write(content)
        return "SUCCESS"
    except Exception as e:
        return f"Error writing file: {e}"

@tool
def patch_file(filepath: str, search_string: str, replace_string: str) -> str:
    """Targeted file patching to prevent full file rewrites. Use for large files."""
    target = Path(filepath)
    if not _is_safe_path(target, [WORKSPACE_OUTBOX]):
        return f"Error: Access denied: Can only patch files in {WORKSPACE_OUTBOX}."
    
    try:
        with open(target, 'r') as f:
            content = f.read()
            
        if search_string not in content:
            return f"Error: Search string not found in {filepath}."
            
        new_content = content.replace(search_string, replace_string, 1) # Replace first exact match
        
        with open(target, 'w') as f:
            f.write(new_content)
        return "SUCCESS"
    except Exception as e:
        return f"Error patching file: {e}"
