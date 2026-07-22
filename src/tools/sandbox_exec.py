import os
import time
import json
import uuid
from langchain_core.tools import tool
from src.core.config import settings
from src.core.logging_config import sandbox_logger as logger

@tool
def run_in_sandbox(command: str, timeout: int = 30) -> dict:
    """Executes a shell command by sending it to the sandbox via filesystem exchange."""
    task_id = f"task_{uuid.uuid4().hex}"
    task_file = os.path.join(settings.INBOX_DIR, f"{task_id}.sh")
    result_file = os.path.join(settings.OUTBOX_DIR, f"{task_id}.sh.json")
    
    try:
        # Write task to inbox
        with open(task_file, "w") as f:
            f.write(command)
        
        # Poll for result
        start_time = time.time()
        while time.time() - start_time < timeout:
            if os.path.exists(result_file):
                # Read result
                with open(result_file, "r") as f:
                    result = json.load(f)
                
                # Cleanup both result and task files
                os.remove(result_file)
                if os.path.exists(task_file):
                    os.remove(task_file)
                return result
            
            time.sleep(0.5)
            
        # Timeout occurred
        logger.warning(f"Sandbox execution timed out after {timeout} seconds.")
        # Try to clean up the orphaned task file if it wasn't picked up
        if os.path.exists(task_file):
            os.remove(task_file)
            
        return {
            "status": "timeout",
            "stdout": "",
            "stderr": "Execution timed out waiting for sandbox.",
            "exit_code": -1
        }
        
    except Exception as e:
        logger.error(f"Sandbox execution failed critically: {e}")
        return {
            "status": "error",
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1
        }
