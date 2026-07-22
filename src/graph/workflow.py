import json
import hashlib
import asyncio
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
from src.tools.web_tools import web_fetch, grep_workspace, http_request
from src.tools.registry import tool_registry
from langchain_core.messages import ToolMessage

TOOLS_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "patch_file": patch_file,
    "run_in_sandbox": run_in_sandbox,
    "web_fetch": web_fetch,
    "grep_workspace": grep_workspace,
    "http_request": http_request
}

# Register all tools with the global registry
tool_registry.bulk_register(TOOLS_MAP)

# Lazy LLM initialization — avoids crash if Ollama isn't running at import time
_llm_instance = None
_overseer_llm_instance = None

def get_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatOllama(model=settings.LLM_MODEL, base_url=settings.OLLAMA_API_BASE).bind_tools(list(TOOLS_MAP.values()))
    return _llm_instance

def get_overseer_llm():
    """Returns a plain LLM (no tools) for the Overseer. Uses REVIEW_MODEL if configured, else LLM_MODEL."""
    global _overseer_llm_instance
    if _overseer_llm_instance is None:
        model = getattr(settings, 'REVIEW_MODEL', None) or settings.LLM_MODEL
        _overseer_llm_instance = ChatOllama(model=model, base_url=settings.OLLAMA_API_BASE)
    return _overseer_llm_instance

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
                try:
                    rows = await conn.fetch(
                        "SELECT skill_abstraction FROM agent_skills ORDER BY embedding <-> $1 LIMIT 1",
                        emb_str
                    )
                finally:
                    await conn.close()
                if rows:
                    skill_context = f"\n<RELEVANT_PAST_EXPERIENCE>\n{rows[0]['skill_abstraction']}\n</RELEVANT_PAST_EXPERIENCE>"
        except Exception as e:
            logger.error(f"RAG Skill Retrieval Error: {e}")

    # Real LLM generation
    sys_msg = SystemMessage(content=(
        "You are Agentic OS, executing tasks in a secure sandbox.\n"
        "<SYSTEM_PROMPT>\n"
        "When modifying files larger than 50 lines, you MUST use the `patch_file` tool instead of `write_file`.\n"
        "</SYSTEM_PROMPT>\n"
        "<CLARIFICATION_PROTOCOL>\n"
        "If the user's request is missing critical parameters (file paths, URLs, port numbers, target names, "
        "credentials, or any value you would otherwise have to guess), do NOT assume defaults. Instead, respond "
        "with ONLY the following XML block and nothing else:\n"
        '<CLARIFICATION_NEEDED>{"question": "your question here", "missing_params": ["param1"]}</CLARIFICATION_NEEDED>\n'
        "</CLARIFICATION_PROTOCOL>"
        f"{skill_context}"
    ))
    
    msgs = [sys_msg]
    msgs.extend(messages)
    
    try:
        # Stream tokens for real-time UI display
        full_content = ""
        response = None
        task_id = current_task.task_id if current_task else ""
        stream_conn = await asyncpg.connect(DB_URL)
        try:
            # LangChain .stream() is synchronous — collect chunks via to_thread
            # to avoid blocking the event loop.
            def _collect_stream():
                nonlocal full_content, response
                for chunk in get_llm().stream(msgs):
                    token = getattr(chunk, "content", "") or ""
                    if token:
                        full_content += token
                    if getattr(chunk, "tool_calls", None):
                        response = chunk

            await asyncio.to_thread(_collect_stream)

            # Broadcast the assembled text as a single notification
            if full_content:
                await stream_conn.execute(
                    "SELECT pg_notify('llm_stream_channel', $1)",
                    json.dumps({"token": full_content, "task_id": task_id})
                )
        finally:
            await stream_conn.close()
        
        # If we got tool calls, use the chunk that had them; otherwise build an AIMessage
        if response is None:
            response = AIMessage(content=full_content)
        elif not getattr(response, "content", ""):
            response.content = full_content
        
        # Check if the LLM is requesting clarification
        content = getattr(response, "content", "") or ""
        if "<CLARIFICATION_NEEDED>" in content and "</CLARIFICATION_NEEDED>" in content:
            if current_task:
                current_task.status = TaskStatus.REQUIRES_CLARIFICATION
            return {"messages": [response], "current_task": current_task}
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
    overseer_count = state.get("overseer_invocation_count", 0) + 1
    
    # If the Overseer has already been invoked MAX_OVERSEER_RETRIES times, give up
    if overseer_count > settings.MAX_OVERSEER_RETRIES:
        current_task = state.get("current_task")
        if current_task:
            current_task.status = TaskStatus.ERROR
        return {
            "messages": [SystemMessage(content="<SYSTEM_OVERRIDE> Maximum Overseer retries exhausted. Routing task to ERROR.")],
            "current_task": current_task,
            "overseer_invocation_count": overseer_count
        }
    
    # Build failure context from recent messages
    messages = state.get("messages", [])
    recent_history = []
    for m in messages[-10:]:
        content = getattr(m, "content", "")
        if content:
            role = type(m).__name__
            recent_history.append(f"[{role}] {content[:500]}")
    failure_context = "\n".join(recent_history)
    
    # Use a plain LLM (no tools) for the Overseer analysis
    overseer_llm = get_overseer_llm()
    overseer_prompt = SystemMessage(content=(
        "You are the Agentic OS Overseer (Constitution Node). You do NOT solve the user's task.\n"
        "Your role is to analyze WHY the worker agent failed repeatedly and inject a mandatory "
        "strategic directive to break the failure loop.\n\n"
        "Rules:\n"
        "1. Read the failure history below carefully.\n"
        "2. Identify the ROOT CAUSE of repeated failures.\n"
        "3. Output a single <SYSTEM_OVERRIDE> directive telling the worker what to STOP doing "
        "and what NEW approach to use instead.\n"
        "4. Be specific and actionable. Reference actual error messages from the history.\n"
        "5. Keep your response under 200 words.\n"
    ))
    
    try:
        response = overseer_llm.invoke([
            overseer_prompt,
            HumanMessage(content=f"FAILURE HISTORY (last {len(messages[-10:])} messages):\n{failure_context}")
        ])
        override_content = getattr(response, "content", "")
        # Ensure it starts with the override tag
        if "<SYSTEM_OVERRIDE>" not in override_content:
            override_content = f"<SYSTEM_OVERRIDE> {override_content}"
    except Exception as e:
        logger.error(f"Overseer LLM call failed: {e}")
        override_content = "<SYSTEM_OVERRIDE> Overseer analysis failed. Stop repeating the same approach and try a fundamentally different strategy."
    
    return {
        "messages": [SystemMessage(content=override_content)],
        "tool_error_count": 0,
        "overseer_invocation_count": overseer_count
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
            try:
                await conn.execute(
                    "INSERT INTO agent_skills (task_intent, skill_abstraction, embedding) VALUES ($1, $2, $3)",
                    skill["task_intent"], skill["skill_abstraction"], str(skill["embedding"])
                )
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error saving skill: {e}")
            
        return {
            "messages": [SystemMessage(content="Task completed and experience saved to pgvector.")]
        }
    return {"tool_error_count": state.get("tool_error_count", 0)}

def route_from_thinking(state: GraphState) -> str:
    if state["current_task"] and state["current_task"].status == TaskStatus.REVIEW:
        return END
    
    # If the LLM requested clarification, stop the graph — the worker will suspend the task
    if state["current_task"] and state["current_task"].status == TaskStatus.REQUIRES_CLARIFICATION:
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

def route_from_review(state: GraphState) -> str:
    # If the task was marked ERROR by the Overseer (max retries exhausted), stop
    current_task = state.get("current_task")
    if current_task and current_task.status == TaskStatus.ERROR:
        return END
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
    workflow.add_conditional_edges("Node_Review", route_from_review)
    workflow.add_edge("Node_Result", END)
    
    return workflow.compile(checkpointer=checkpointer)
