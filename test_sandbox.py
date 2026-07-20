import os
import sys

# Ensure src module can be found
sys.path.append(os.path.dirname(__file__))

from src.tools.sandbox_exec import run_in_sandbox

def test():
    print("Sending command to sandbox: 'echo Hello from sandbox'")
    result = run_in_sandbox("echo Hello from sandbox")
    print("Result:")
    print(result)

if __name__ == "__main__":
    test()
