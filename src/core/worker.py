import asyncio
import json
import logging
import re
import asyncpg
from src.core.config import settings
from src.core.models import GraphState, TaskObject, TaskStatus
from src.graph.workflow import create_graph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage
from psycopg_pool import AsyncConnectionPool

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import json
original_dump_metadata = AsyncPostgresSaver._dump_metadata
def patched_dump_metadata(self, metadata):
    try:
        return original_dump_metadata(self, metadata)
    except TypeError:
        return json.dumps(metadata, default=str)
AsyncPostgresSaver._dump_metadata = patched_dump_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_serialize(obj):
    try:
        # Convert Pydantic / LangChain messages to dict, then recursively sanitize
        # the result since nested fields (e.g. raw ollama.Message objects) may
        # still be non-JSON-serializable.
        if hasattr(obj, "dict"):
            return safe_serialize(obj.dict())
        elif isinstance(obj, list):
            return [safe_serialize(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: safe_serialize(v) for k, v in obj.items()}
        elif isinstance(obj, (int, float, bool, type(None))):
            return obj
        else:
            return str(obj)
    except Exception:
        return str(obj)

async def run_worker():
    pool = await asyncpg.create_pool(settings.DATABASE_URL)
    
    logger.info("AgenticOS Background Worker Started (event-driven via LISTEN/NOTIFY).")
    
    # --- Event-driven wake-up via PostgreSQL LISTEN/NOTIFY ---
    task_event = asyncio.Event()
    listen_conn = await pool.acquire()
    
    def _on_notify(connection, pid, channel, payload):
        task_event.set()
    
    await listen_conn.add_listener("system_tasks_channel", _on_notify)
    
    async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
        await checkpointer.setup()
        app = create_graph(checkpointer)
        
        while True:
            msg_id = None
            try:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT message_id, payload, workspace_id FROM system_tasks WHERE status = 'USER_INPUT' ORDER BY created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED"
                    )
                    if row:
                        msg_id = row['message_id']
                        payload = json.loads(row['payload'])
                        workspace_id = row['workspace_id'] or 1
                        
                        await conn.execute("UPDATE system_tasks SET status = 'PENDING' WHERE message_id = $1", msg_id)
                        
                        task = TaskObject(**payload)
                        task.status = TaskStatus.PENDING
                        
                        # --- Short-Term Memory: inject workspace chat history ---
                        history_messages = []
                        try:
                            history_rows = await conn.fetch(
                                "SELECT payload FROM system_tasks "
                                "WHERE workspace_id = $1 AND message_id != $2 "
                                "AND status IN ('RESULT_OUTPUT', 'ERROR') "
                                "ORDER BY created_at DESC LIMIT $3",
                                workspace_id, msg_id, settings.CHAT_HISTORY_LIMIT
                            )
                            # Rows are newest-first; reverse to chronological order
                            for hrow in reversed(history_rows):
                                try:
                                    hp = json.loads(hrow['payload'])
                                    if hp.get('intent'):
                                        history_messages.append(HumanMessage(content=hp['intent']))
                                    if hp.get('response'):
                                        history_messages.append(AIMessage(content=hp['response']))
                                except (json.JSONDecodeError, KeyError):
                                    pass
                        except Exception as hist_err:
                            logger.warning(f"Failed to load chat history: {hist_err}")
                        
                        # Append the current task intent as the latest message
                        history_messages.append(HumanMessage(content=task.intent))
                        
                        state = {
                            "current_task": task,
                            "tool_error_count": 0,
                            "failed_tool_hashes": [],
                            "messages": history_messages,
                            "overseer_invocation_count": 0
                        }
                        
                        logger.info(f"Executing task: {task.intent} in workspace {workspace_id}")
                        
                        config = {"configurable": {"thread_id": str(workspace_id)}}
                        
                        last_response_text = None
                        
                        async def _run_graph():
                            nonlocal last_response_text
                            async for event in app.astream(state, config=config, stream_mode="updates"):
                                for node_name, state_diff in event.items():
                                    serialized_diff = safe_serialize(state_diff)
                                    await conn.execute(
                                        "INSERT INTO system_debug_trace (task_id, node_name, state_diff) VALUES ($1, $2, $3)",
                                        msg_id, node_name, json.dumps(serialized_diff)
                                    )
                                    logger.info(f"[{node_name}] Executed.")
                                    
                                    # Capture the latest human-readable message so the Chat UI can render a real reply
                                    if node_name in ("Node_Worker_Thinking", "Node_Review", "Node_Tool_Execution"):
                                        for m in state_diff.get("messages", []):
                                            content = getattr(m, "content", None)
                                            if content:
                                                last_response_text = content
                        
                        try:
                            await asyncio.wait_for(_run_graph(), timeout=settings.TASK_TIMEOUT_SECONDS)
                        except asyncio.TimeoutError:
                            logger.error(f"Task {msg_id} timed out after {settings.TASK_TIMEOUT_SECONDS}s.")
                            # Use a fresh connection since the cancelled coroutine may have left conn in a bad state
                            async with pool.acquire() as err_conn:
                                await err_conn.execute(
                                    "UPDATE system_tasks SET status = 'ERROR', payload = payload || $2::jsonb WHERE message_id = $1",
                                    msg_id, json.dumps({"response": f"Error: task timed out after {settings.TASK_TIMEOUT_SECONDS}s."})
                                )
                            continue
                        
                        # Check if the graph suspended for clarification
                        clarification_question = None
                        if last_response_text and "<CLARIFICATION_NEEDED>" in last_response_text:
                            match = re.search(r'<CLARIFICATION_NEEDED>(.*?)</CLARIFICATION_NEEDED>', last_response_text, re.DOTALL)
                            if match:
                                try:
                                    clar_data = json.loads(match.group(1))
                                    clarification_question = clar_data.get("question", "Please provide more details.")
                                except json.JSONDecodeError:
                                    clarification_question = match.group(1).strip()
                        
                        if clarification_question:
                            await conn.execute(
                                "UPDATE system_tasks SET status = 'REQUIRES_CLARIFICATION', payload = payload || $2::jsonb WHERE message_id = $1",
                                msg_id, json.dumps({"clarification_question": clarification_question})
                            )
                            logger.info(f"Task {msg_id} suspended for clarification: {clarification_question}")
                        # Update status and surface the final response text to the Chat UI
                        elif last_response_text:
                            await conn.execute(
                                "UPDATE system_tasks SET status = 'RESULT_OUTPUT', payload = payload || $2::jsonb WHERE message_id = $1",
                                msg_id, json.dumps({"response": last_response_text})
                            )
                        else:
                            await conn.execute("UPDATE system_tasks SET status = 'RESULT_OUTPUT' WHERE message_id = $1", msg_id)
                        
            except Exception as e:
                import traceback
                logger.error(f"Worker error: {e}")
                logger.error(traceback.format_exc())
                # Never leave a claimed task stuck at PENDING forever - surface the failure instead.
                if msg_id:
                    try:
                        async with pool.acquire() as conn:
                            await conn.execute(
                                "UPDATE system_tasks SET status = 'ERROR', payload = payload || $2::jsonb WHERE message_id = $1 AND status != 'RESULT_OUTPUT'",
                                msg_id, json.dumps({"response": f"Error: {e}"})
                            )
                    except Exception as inner_e:
                        logger.error(f"Failed to mark task {msg_id} as ERROR: {inner_e}")
                
            # Wait for a NOTIFY event or fallback poll after timeout
            task_event.clear()
            try:
                await asyncio.wait_for(task_event.wait(), timeout=settings.WORKER_FALLBACK_POLL_SECONDS)
            except asyncio.TimeoutError:
                pass

if __name__ == "__main__":
    asyncio.run(run_worker())
