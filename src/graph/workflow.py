import os
import json
import hashlib
import asyncpg
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, SystemMessage
from src.core.models import GraphState, TaskStatus
from src.maintenance.idle_daemon import generate_skill_from_task
from src.core.config import settings

DB_URL = settings.DATABASE_URL

def hash_tool_call(tool_name: str, parameters: Dict[str, Any]) -> str:
    # Deterministic hash to prevent LLM tunnel vision loops
    tool_data = f"{tool_name}:{json.dumps(parameters, sort_keys=True)}"
    return hashlib.sha256(tool_data.encode()).hexdigest()

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from src.tools.file_io import read_file, write_file, patch_file
from src.tools.sandbox_exec import run_in_sandbox
from langchain_core.messages import ToolMessage

TOOLS_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "patch_file": patch_file,
    "run_in_sandbox": run_in_sandbox
}

llm = ChatOllama(model=settings.LLM_MODEL, base_url=settings.OLLAMA_API_BASE).bind_tools(list(TOOLS_MAP.values()))

from src.core.logging_config import orchestrator_logger as logger

async def node_worker_thinking(state: GraphState) -> Dict[str, Any]:
    current_task = state.get("current_task")
    messages = state.get("messages", [])
    
    logger.info(f"Orchestrator node_worker_thinking triggered for task: {current_task.intent if current_task else 'Unknown'}")
    
    # Retrieval Augmented Generation (RAG) for Skills
    skill_context = ""
    if current_task:
        try:
            from src.maintenance.idle_daemon import get_embedding
            emb = get_embedding(current_task.intent)
            if emb and len(emb) == 768:
                # Format as pgvector string
                emb_str = "[" + ",".join(str(x) for x in emb) + "]"
                conn = await asyncpg.connect(DB_URL)
                rows = await conn.fetch(
                    "SELECT skill_abstraction FROM agent_skills ORDER BY embedding <-> $1 LIMIT 1",
                    emb_str
                )
                await conn.close()
                if rows:
                    skill_context = f"\n<RELEVANT_PAST_EXPERIENCE>\n{rows[0]['skill_abstraction']}\n</RELEVANT_PAST_EXPERIENCE>"
        except Exception as e:
            logger.error(f"RAG Skill Retrieval Error: {e}")

    # Real LLM generation
    sys_msg = SystemMessage(content=f"You are Agentic OS, executing tasks in a secure sandbox.\n<SYSTEM_PROMPT> When modifying files larger than 50 lines, you MUST use the `patch_file` tool instead of `write_file`.</SYSTEM_PROMPT>{skill_context}")
    
    msgs = [sys_msg]
    msgs.extend(messages)
    
    try:
        response = llm.invoke(msgs)
        return {"messages": [response]}
    except Exception as e:
        return {"messages": [SystemMessage(content=f"LLM execution failed: {e}")]}

def node_tool_execution(state: GraphState) -> Dict[str, Any]:
    # Level 1 Protection: The Tool-Scanner
    messages = state.get("messages", [])
    failed_tool_hashes = state.get("failed_tool_hashes", [])
    tool_error_count = state.get("tool_error_count", 0)
    
    last_msg = messages[-1] if messages else None
    
    if last_msg and getattr(last_msg, "tool_calls", None):
        tc = last_msg.tool_calls[0]
        t_hash = hash_tool_call(tc["name"], tc["args"])
        
        if t_hash in failed_tool_hashes:
            # Block the repeated execution immediately
            return {
                "tool_error_count": tool_error_count + 1,
                "messages": [ToolMessage(
                    content="System block: This exact tool call already failed. Generate a completely new approach.",
                    tool_call_id=tc["id"],
                    name=tc["name"]
                )]
            }
        else:
            # ACTUALLY EXECUTE THE TOOL
            try:
                if tc["name"] not in TOOLS_MAP:
                    raise ValueError(f"Unknown tool: {tc['name']}")
                    
                tool_fn = TOOLS_MAP[tc["name"]]
                result = tool_fn.invoke(tc["args"])
                
                return {
                    "messages": [ToolMessage(
                        content=str(result),
                        tool_call_id=tc["id"],
                        name=tc["name"]
                    )]
                }
            except Exception as e:
                return {
                    "failed_tool_hashes": failed_tool_hashes + [t_hash],
                    "tool_error_count": tool_error_count + 1,
                    "messages": [ToolMessage(
                        content=f"Tool failed: {e}",
                        tool_call_id=tc["id"],
                        name=tc["name"]
                    )]
                }
    return {"tool_error_count": tool_error_count}

def node_review(state: GraphState) -> Dict[str, Any]:
    # Level 2 Protection: The Constitution Node (Overseer)
    return {
        "messages": [SystemMessage(content="<SYSTEM_OVERRIDE> Stop using the failing approach. Try browser automation instead.")]
    }

async def node_result(state: GraphState) -> Dict[str, Any]:
    """Experience Consolidation: Save learned abstractions to pgvector."""
    current_task = state.get("current_task")
    messages = state.get("messages", [])
    if current_task:
        intent = current_task.intent
        history = "\n".join([m.content for m in messages if isinstance(m.content, str)])
        
        skill = generate_skill_from_task(intent, history)
        
        try:
            conn = await asyncpg.connect(DB_URL)
            await conn.execute(
                "INSERT INTO agent_skills (task_intent, skill_abstraction, embedding) VALUES ($1, $2, $3)",
                skill["task_intent"], skill["skill_abstraction"], str(skill["embedding"])
            )
            await conn.close()
        except Exception as e:
            print(f"Error saving skill: {e}")
            
        return {
            "messages": [SystemMessage(content="Task completed and experience saved to pgvector.")]
        }
    return {"tool_error_count": state.get("tool_error_count", 0)}

def route_from_thinking(state: GraphState) -> str:
    if state["current_task"] and state["current_task"].status == TaskStatus.REVIEW:
        return END
    
    last_msg = state["messages"][-1] if state["messages"] else None
    if last_msg and getattr(last_msg, "tool_calls", None):
        return "Node_Tool_Execution"
    
    tool_error_count = state.get("tool_error_count", 0)
    if tool_error_count >= 3:
        return "Node_Review"
        
    return "Node_Result"

def route_from_tool(state: GraphState) -> str:
    if state["tool_error_count"] >= 3:
        return "Node_Review"
    return "Node_Worker_Thinking"

def create_graph(checkpointer=None) -> StateGraph:
    workflow = StateGraph(GraphState)
    
    workflow.add_node("Node_Worker_Thinking", node_worker_thinking)
    workflow.add_node("Node_Tool_Execution", node_tool_execution)
    workflow.add_node("Node_Review", node_review)
    workflow.add_node("Node_Result", node_result)
    
    workflow.set_entry_point("Node_Worker_Thinking")
    
    workflow.add_conditional_edges("Node_Worker_Thinking", route_from_thinking)
    workflow.add_conditional_edges("Node_Tool_Execution", route_from_tool)
    workflow.add_edge("Node_Review", "Node_Worker_Thinking")
    workflow.add_edge("Node_Result", END)
    
    return workflow.compile(checkpointer=checkpointer)
