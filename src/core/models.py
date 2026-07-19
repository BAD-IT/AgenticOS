from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REQUIRES_CLARIFICATION = "REQUIRES_CLARIFICATION"
    FAILED = "FAILED"

class QueueName(str, Enum):
    USER_INPUT = "User_Input_Queue"
    TASKS = "Tasks_Queue"
    PENDING = "Pending_Queue"
    REVIEW = "Review_Queue"
    RESULT_OUTPUT = "Result_Output_Queue"
    NOTIFICATION = "Notification_Queue"
    ERROR = "Error_Queue"

class TaskObject(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the task")
    intent: str = Field(..., description="The raw intent or command")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current status of the task")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parsed parameters required for execution")

class GraphState(BaseModel):
    tool_error_count: int = Field(default=0, description="Counter for consecutive tool errors to trigger circuit breaker")
    failed_tool_hashes: List[str] = Field(default_factory=list, description="List of hashes for failed tool executions to prevent looping")
    current_task: Optional[TaskObject] = Field(default=None, description="The task currently being processed")

class QueueMessage(BaseModel):
    message_id: str = Field(..., description="Unique identifier for the queue message")
    queue_name: QueueName = Field(..., description="The target queue for this message")
    payload: Dict[str, Any] = Field(..., description="The message payload, usually a serialized TaskObject or Error log")
    created_at: str = Field(..., description="Timestamp of message creation")
