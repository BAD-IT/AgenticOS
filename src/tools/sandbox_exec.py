import subprocess
from src.core.logging_config import sandbox_logger as logger

def run_in_sandbox(command: str, timeout: int = 30) -> dict:
    """Executes a shell command inside the isolated agenticos_artifact_runner container."""
    try:
        # Utilize the docker SDK or subprocess to execute securely inside the isolated container
        result = subprocess.run(
            ["docker", "exec", "agenticos_artifact_runner", "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired as e:
        logger.warning(f"Sandbox execution timed out after {timeout} seconds.")
        return {
            "status": "timeout",
            "stdout": e.stdout.decode() if e.stdout else "",
            "stderr": e.stderr.decode() if e.stderr else "TimeoutExpired",
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
