from src.core.models import TaskObject, TaskStatus, GraphState, QueueMessage, QueueName
from pydantic import ValidationError

print("--- Testing Valid Model Instantiation ---")
task = TaskObject(
    task_id="task_123",
    intent="Deploy the app",
    status=TaskStatus.REQUIRES_CLARIFICATION
)
print(f"Task Object created successfully: {task.task_id} with status {task.status}")

print("\n--- Testing Invalid Data Type (Intentional Failure) ---")
try:
    bad_task = TaskObject(
        task_id="task_456",
        intent="Deploy the app",
        status="NOT_A_VALID_STATUS"
    )
    print("ERROR: Should not have created bad_task!")
except ValidationError as e:
    print("SUCCESS: Caught expected ValidationError for invalid status.")
    print(e)
    
try:
    bad_state = GraphState(
        tool_error_count="should be an int"
    )
    print("ERROR: Should not have created bad_state!")
except ValidationError as e:
    print("SUCCESS: Caught expected ValidationError for invalid int.")
    print(e)
