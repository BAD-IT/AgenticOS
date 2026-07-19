from src.graph.workflow import create_graph, node_tool_execution, node_worker_thinking, node_review
from src.core.models import GraphState, TaskObject, TaskStatus
from langchain_core.messages import AIMessage

print("\n--- Test 3: Proactive Clarification ---")
app = create_graph()
state_t3 = {"current_task": TaskObject(task_id="t3", intent="Deploy", parameters={})}
res3 = app.invoke(state_t3)
print(f"Final Task Status: {res3['current_task'].status}")
print(f"Message output: {res3['messages'][-1].content}")
assert res3['current_task'].status == TaskStatus.REQUIRES_CLARIFICATION

print("\n--- Test 1: Level 1 Tool-Scanner (Hashing Block) ---")
# Manually run the node for clear terminal testing
tc = {"name": "read_file", "args": {"path": "/etc/passwd"}, "id": "call_1"}
msg = AIMessage(content="", tool_calls=[tc])

# First execution (fails normally)
state_t1 = GraphState(
    current_task=TaskObject(task_id="t1", intent="Read", parameters={"path": "/etc/passwd"}),
    messages=[msg],
    failed_tool_hashes=[]
)
update_1 = node_tool_execution(state_t1)
print(f"First Execution Output: {update_1['messages'][0].content}")

# Simulated repeated execution
state_t1.failed_tool_hashes = update_1["failed_tool_hashes"]
update_2 = node_tool_execution(state_t1)
print(f"Second Execution Output: {update_2['messages'][0].content}")
print(f"Error Count Incremented to: {update_2['tool_error_count']}")
assert "System block" in update_2['messages'][0].content

print("\n--- Test 2: Level 2 Protection (The Constitution Node) ---")
state_t2 = GraphState(tool_error_count=3)
update_3 = node_review(state_t2)
print(f"Overseer Output: {update_3['messages'][0].content}")
assert "<SYSTEM_OVERRIDE>" in update_3['messages'][0].content

print("\nSUCCESS: All LangGraph and Circuit Breaker logic passed!")
