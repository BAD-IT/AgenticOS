from enum import Enum
from typing import List, Optional, Any, Dict, Annotated
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class TaskStatus(str, Enum):
    USER_INPUT = "USER_INPUT"
    TASK = "TASK"
    PENDING = "PENDING"
    REVIEW = "REVIEW"
    RESULT_OUTPUT = "RESULT_OUTPUT"
    ERROR = "ERROR"

class TaskObject(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the task")
    intent: str = Field(..., description="The raw intent or command")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current status of the task")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parsed parameters required for execution")

from typing import TypedDict

class GraphState(TypedDict):
    current_task: Optional[TaskObject]
    tool_error_count: int
    failed_tool_hashes: List[str]
    messages: Annotated[List[BaseMessage], add_messages]
