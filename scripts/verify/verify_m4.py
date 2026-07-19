import subprocess
import os
from src.tools.sandbox_exec import run_in_sandbox
from src.tools.file_io import write_file, patch_file

print("--- Preparing Sandbox ---")
print("Compiling C++ test inside the isolated runner...")

print("\n--- Test 1: Execution (C++ Hello World) ---")
cpp_code = """
#include <iostream>
int main() {
    std::cout << "Hello from C++ Sandbox!" << std::endl;
    return 0;
}
"""
write_file("workspace/outbox/hello.cpp", cpp_code)
# Compile and run
compile_res = run_in_sandbox("g++ /sandbox/hello.cpp -o /sandbox/hello")
run_res = run_in_sandbox("/sandbox/hello")
print(f"Compilation: {compile_res['status']}")
print(f"Execution Output: {run_res['stdout'].strip()}")
assert "Hello from C++ Sandbox!" in run_res['stdout']

print("\n--- Test 2: Safety (Infinite Loop Timeout) ---")
py_code = """
while True:
    pass
"""
write_file("workspace/outbox/loop.py", py_code)
print("Executing infinite loop with a 3-second timeout...")
loop_res = run_in_sandbox("python /sandbox/loop.py", timeout=3)
print(f"Status: {loop_res['status']}")
print(f"Stderr: {loop_res['stderr']}")
assert loop_res['status'] == 'timeout'

print("\n--- Test 3: Patching (Targeted Patch on 500-line file) ---")
large_file_content = ["def foo():\n    return 'old_foo'"] + ["# Line " + str(i) for i in range(2, 501)]
write_file("workspace/outbox/large_file.py", "\n".join(large_file_content))

print("Patching foo()...")
patch_file("workspace/outbox/large_file.py", "return 'old_foo'", "return 'NEW_PATCHED_FOO'")

with open("workspace/outbox/large_file.py", "r") as f:
    patched_content = f.read()

print(f"Patched File lines: {len(patched_content.splitlines())}")
print(f"First 2 lines: {patched_content.splitlines()[:2]}")
assert "return 'NEW_PATCHED_FOO'" in patched_content
assert len(patched_content.splitlines()) == 501

print("\nSUCCESS: All M4 Tools and Sandbox integrations passed!")
