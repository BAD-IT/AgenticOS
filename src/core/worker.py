import asyncio
import json
import logging
import re
import traceback
import urllib.request
import asyncpg
from src.core.config import settings
from src.core.models import GraphState, TaskObject, TaskStatus
from src.core.logging_config import current_task_id
from src.graph.workflow import create_graph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage
from src.maintenance.idle_daemon import run_idle_daemon

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

def _fire_webhook_sync(url: str, message_id: str, payload: str, task_status: str):
    """Blocking webhook POST — called via asyncio.to_thread to avoid blocking the event loop."""
    data = json.dumps({"message_id": message_id, "payload": payload, "status": task_status}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=10)

async def _fire_webhook(url: str, message_id: str, payload: str, task_status: str):
    """Fire-and-forget outbound webhook notification on task completion."""
    try:
        await asyncio.to_thread(_fire_webhook_sync, url, message_id, payload, task_status)
        logger.info(f"Webhook delivered to {url} for task {message_id}")
    except Exception as e:
        logger.warning(f"Webhook delivery failed for {url}: {e}")

async def run_worker():
    pool = await asyncpg.create_pool(settings.DATABASE_URL)
    
    logger.info("AgenticOS Background Worker Started (event-driven via LISTEN/NOTIFY).")
    
    # --- Event-driven wake-up via PostgreSQL LISTEN/NOTIFY ---
    task_event = asyncio.Event()
    listen_conn = await pool.acquire()
    
    def _on_notify(connection, pid, channel, payload):
        task_event.set()
    
    await listen_conn.add_listener("system_tasks_channel", _on_notify)
    
    # Launch the idle daemon as a background task
    asyncio.create_task(run_idle_daemon(pool))
    
    async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
        await checkpointer.setup()
        app = create_graph(checkpointer)
        
        while True:
            msg_id = None
            try:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT message_id, payload, workspace_id FROM system_tasks WHERE status = 'USER_INPUT' ORDER BY priority ASC, created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED"
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
                                        resp = hp['response']
                                        # Truncate long AI responses to keep context manageable
                                        if len(resp) > 500:
                                            resp = resp[:500] + "... [truncated]"
                                        history_messages.append(AIMessage(content=resp))
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
                        
                        current_task_id.set(msg_id)
                        logger.info(f"[LIFECYCLE] Task claimed: msg_id={msg_id}, intent='{task.intent}', workspace={workspace_id}")
                        logger.info(f"[LIFECYCLE] Chat history injected: {len(history_messages)} messages (including current)")
                        
                        # Use msg_id (unique per task) as thread_id — NOT workspace_id.
                        # Workspace chat history is already injected from the DB above.
                        # Using workspace_id would accumulate ALL messages from ALL tasks
                        # in the LangGraph checkpoint, causing unbounded context growth.
                        config = {"configurable": {"thread_id": msg_id}}
                        
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
                                    logger.info(f"[LIFECYCLE] Node executed: {node_name}")
                                    
                                    # Capture the latest human-readable message so the Chat UI can render a real reply
                                    if node_name in ("Node_Worker_Thinking", "Node_Review", "Node_Tool_Execution"):
                                        for m in state_diff.get("messages", []):
                                            content = getattr(m, "content", None)
                                            if content:
                                                last_response_text = content
                                                preview = content[:200].replace('\n', ' ')
                                                logger.info(f"[LIFECYCLE] LLM response captured from {node_name}: '{preview}...'")
                                    
                                    # Log task status changes from graph nodes
                                    task_in_diff = state_diff.get("current_task")
                                    if task_in_diff:
                                        logger.info(f"[LIFECYCLE] Task status after {node_name}: {getattr(task_in_diff, 'status', 'unknown')}")
                        
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
                        logger.info(f"[LIFECYCLE] Graph finished. last_response_text={'set (' + str(len(last_response_text)) + ' chars)' if last_response_text else 'None'}")
                        if last_response_text:
                            logger.info(f"[LIFECYCLE] Full response: {last_response_text[:500]}")
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
                            logger.info(f"[LIFECYCLE] Task {msg_id} → REQUIRES_CLARIFICATION: {clarification_question}")
                        # Update status and surface the final response text to the Chat UI
                        elif last_response_text:
                            logger.info(f"[LIFECYCLE] Task {msg_id} → RESULT_OUTPUT (with response)")
                            await conn.execute(
                                "UPDATE system_tasks SET status = 'RESULT_OUTPUT', payload = payload || $2::jsonb WHERE message_id = $1",
                                msg_id, json.dumps({"response": last_response_text})
                            )
                        else:
                            logger.warning(f"[LIFECYCLE] Task {msg_id} → RESULT_OUTPUT (NO response text captured!)")
                            await conn.execute("UPDATE system_tasks SET status = 'RESULT_OUTPUT' WHERE message_id = $1", msg_id)
                        
                        # --- Outbound Webhook ---
                        row_after = await conn.fetchrow(
                            "SELECT webhook_url, payload, status FROM system_tasks WHERE message_id = $1", msg_id
                        )
                        if row_after and row_after['webhook_url']:
                            asyncio.create_task(_fire_webhook(row_after['webhook_url'], msg_id, row_after['payload'], row_after['status']))
                        
            except asyncio.CancelledError:
                logger.info("Worker received shutdown signal.")
                raise
            except Exception as e:
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
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

if __name__ == "__main__":
    asyncio.run(run_worker())
