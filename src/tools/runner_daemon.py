import os
import time
import json
import subprocess
from src.core.config import settings

INBOX_DIR = settings.INBOX_DIR
OUTBOX_DIR = settings.OUTBOX_DIR

def process_tasks():
    while True:
        if os.path.exists(INBOX_DIR):
            for filename in os.listdir(INBOX_DIR):
                if filename.endswith(".sh") and not filename.startswith("."):
                    filepath = os.path.join(INBOX_DIR, filename)
                    result_file = os.path.join(OUTBOX_DIR, f"{filename}.json")

                    # Skip files that already have a result (prevents reprocessing)
                    if os.path.exists(result_file):
                        continue
                    
                    try:
                        with open(filepath, "r") as f:
                            command = f.read()
                        
                        print(f"Executing task: {filename}")
                        
                        try:
                            # Execute securely
                            process = subprocess.run(
                                ["sh", "-c", command],
                                capture_output=True,
                                text=True,
                                timeout=30
                            )
                            result = {
                                "status": "success" if process.returncode == 0 else "error",
                                "stdout": process.stdout,
                                "stderr": process.stderr,
                                "exit_code": process.returncode
                            }
                        except subprocess.TimeoutExpired as e:
                            result = {
                                "status": "timeout",
                                "stdout": e.stdout.decode() if e.stdout else "",
                                "stderr": e.stderr.decode() if e.stderr else "TimeoutExpired",
                                "exit_code": -1
                            }
                        
                        # Write result to outbox
                        with open(result_file, "w") as f:
                            json.dump(result, f)
                        print(f"Result written: {result_file}")
                        
                    except Exception as e:
                        print(f"Critical error processing {filename}: {e}")
                        
        time.sleep(1)

if __name__ == "__main__":
    print("Agentic OS Sandbox Runner initialized.")
    os.makedirs(INBOX_DIR, exist_ok=True)
    os.makedirs(OUTBOX_DIR, exist_ok=True)
    process_tasks()
