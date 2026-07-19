import json
import hashlib
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, SystemMessage
from src.core.models import GraphState, TaskStatus

def hash_tool_call(tool_name: str, parameters: Dict[str, Any]) -> str:
    # Deterministic hash to prevent LLM tunnel vision loops
    tool_data = f"{tool_name}:{json.dumps(parameters, sort_keys=True)}"
    return hashlib.sha256(tool_data.encode()).hexdigest()

def node_worker_thinking(state: GraphState) -> Dict[str, Any]:
    # Proactive Clarification Check (Anti-Hallucination)
    if state.current_task and not state.current_task.parameters:
        state.current_task.status = TaskStatus.REQUIRES_CLARIFICATION
        return {
            "current_task": state.current_task,
            "messages": [SystemMessage(content="Task halted: REQUIRES_CLARIFICATION. Parameters missing.")]
        }
    
    # Normally LLM generation goes here.
    # We mock it for the tests by not generating anything new
    # unless there's specific logic required.
    return {}

def node_tool_execution(state: GraphState) -> Dict[str, Any]:
    # Level 1 Protection: The Tool-Scanner
    last_msg = state.messages[-1] if state.messages else None
    
    if last_msg and getattr(last_msg, "tool_calls", None):
        tc = last_msg.tool_calls[0]
        t_hash = hash_tool_call(tc["name"], tc["args"])
        
        if t_hash in state.failed_tool_hashes:
            # Block the repeated execution immediately
            return {
                "tool_error_count": state.tool_error_count + 1,
                "messages": [SystemMessage(content="System block: This exact tool call already failed. Generate a completely new approach.")]
            }
        else:
            # Mock failure of a valid new tool execution
            return {
                "failed_tool_hashes": [t_hash], # LangGraph will append or we append natively
                "messages": [SystemMessage(content=f"Tool {tc['name']} failed.")]
            }
    return {}

def node_review(state: GraphState) -> Dict[str, Any]:
    # Level 2 Protection: The Constitution Node (Overseer)
    if state.tool_error_count >= 3:
        return {
            "messages": [SystemMessage(content="<SYSTEM_OVERRIDE> Stop using the failing approach. Try browser automation instead.")]
        }
    return {}

def route_from_thinking(state: GraphState) -> str:
    if state.current_task and state.current_task.status == TaskStatus.REQUIRES_CLARIFICATION:
        return END
    
    last_msg = state.messages[-1] if state.messages else None
    if last_msg and getattr(last_msg, "tool_calls", None):
        return "Node_Tool_Execution"
    
    return "Node_Review"

def route_from_tool(state: GraphState) -> str:
    if state.tool_error_count >= 3:
        return "Node_Review"
    return "Node_Worker_Thinking"

def create_graph() -> StateGraph:
    workflow = StateGraph(GraphState)
    
    workflow.add_node("Node_Worker_Thinking", node_worker_thinking)
    workflow.add_node("Node_Tool_Execution", node_tool_execution)
    workflow.add_node("Node_Review", node_review)
    
    workflow.set_entry_point("Node_Worker_Thinking")
    
    workflow.add_conditional_edges("Node_Worker_Thinking", route_from_thinking)
    workflow.add_conditional_edges("Node_Tool_Execution", route_from_tool)
    workflow.add_edge("Node_Review", END)
    
    return workflow.compile()
