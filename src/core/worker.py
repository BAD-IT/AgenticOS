import asyncio
import json
import logging
import asyncpg
from src.core.config import settings
from src.core.models import GraphState, TaskObject, TaskStatus
from src.graph.workflow import create_graph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage
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
        else:
            return str(obj)
    except Exception:
        return str(obj)

async def run_worker():
    pool = await asyncpg.create_pool(settings.DATABASE_URL)
    
    logger.info("AgenticOS Background Worker Started. Polling for tasks...")
    
    async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
        await checkpointer.setup()
        app = create_graph(checkpointer)
        
        while True:
            msg_id = None
            try:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT message_id, payload, workspace_id FROM system_tasks WHERE status = 'USER_INPUT' ORDER BY created_at ASC LIMIT 1"
                    )
                    if row:
                        msg_id = row['message_id']
                        payload = json.loads(row['payload'])
                        workspace_id = row['workspace_id'] or 1
                        
                        await conn.execute("UPDATE system_tasks SET status = 'PENDING' WHERE message_id = $1", msg_id)
                        
                        task = TaskObject(**payload)
                        task.status = TaskStatus.PENDING
                        
                        state = {
                            "current_task": task,
                            "tool_error_count": 0,
                            "failed_tool_hashes": [],
                            "messages": [HumanMessage(content=task.intent)]
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
                            await conn.execute(
                                "UPDATE system_tasks SET status = 'ERROR', payload = payload || $2::jsonb WHERE message_id = $1",
                                msg_id, json.dumps({"response": f"Error: task timed out after {settings.TASK_TIMEOUT_SECONDS}s."})
                            )
                            continue
                        
                        # Update status and surface the final response text to the Chat UI
                        if last_response_text:
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
                
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(run_worker())
