import os
from pathlib import Path

# Base paths (resolving to ensure secure checking)
WORKSPACE_INBOX = Path(os.getenv("INBOX_DIR", "workspace/inbox")).resolve()
WORKSPACE_OUTBOX = Path(os.getenv("OUTBOX_DIR", "workspace/outbox")).resolve()

def _is_safe_path(requested_path: Path, base_paths: list[Path]) -> bool:
    resolved_path = requested_path.resolve()
    for bp in base_paths:
        if resolved_path.is_relative_to(bp):
            return True
    return False

def read_file(filepath: str) -> str:
    target = Path(filepath)
    if not _is_safe_path(target, [WORKSPACE_INBOX, WORKSPACE_OUTBOX]):
        raise PermissionError(f"Access denied: {filepath} is outside the sandbox.")
    with open(target, 'r') as f:
        return f.read()

def write_file(filepath: str, content: str) -> str:
    target = Path(filepath)
    if not _is_safe_path(target, [WORKSPACE_OUTBOX]):
        raise PermissionError(f"Access denied: Can only write to {WORKSPACE_OUTBOX}.")
    
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, 'w') as f:
        f.write(content)
    return "SUCCESS"

def patch_file(filepath: str, search_string: str, replace_string: str) -> str:
    """Targeted file patching to prevent full file rewrites."""
    target = Path(filepath)
    if not _is_safe_path(target, [WORKSPACE_OUTBOX]):
        raise PermissionError(f"Access denied: Can only patch files in {WORKSPACE_OUTBOX}.")
    
    with open(target, 'r') as f:
        content = f.read()
        
    if search_string not in content:
        raise ValueError(f"Search string not found in {filepath}.")
        
    new_content = content.replace(search_string, replace_string, 1) # Replace first exact match
    
    with open(target, 'w') as f:
        f.write(new_content)
    return "SUCCESS"
