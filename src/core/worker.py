import asyncio
import json
import logging
import asyncpg
from src.core.config import settings
from src.core.models import GraphState, TaskObject, TaskStatus
from src.graph.workflow import create_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_serialize(obj):
    try:
        # Convert Pydantic / LangChain messages to dict
        if hasattr(obj, "dict"):
            return obj.dict()
        elif isinstance(obj, list):
            return [safe_serialize(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: safe_serialize(v) for k, v in obj.items()}
        else:
            return str(obj)
    except Exception:
        return str(obj)

async def run_worker():
    app = create_graph()
    pool = await asyncpg.create_pool(settings.DATABASE_URL)
    
    logger.info("AgenticOS Background Worker Started. Polling for tasks...")
    
    while True:
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT message_id, payload FROM system_tasks WHERE status = 'USER_INPUT' ORDER BY created_at ASC LIMIT 1"
                )
                if row:
                    msg_id = row['message_id']
                    payload = json.loads(row['payload'])
                    
                    await conn.execute("UPDATE system_tasks SET status = 'PENDING' WHERE message_id = $1", msg_id)
                    
                    task = TaskObject(**payload)
                    task.status = TaskStatus.PENDING
                    
                    state = GraphState(
                        current_task=task,
                        tool_error_count=0,
                        failed_tool_hashes=[],
                        messages=[]
                    )
                    
                    logger.info(f"Executing task: {task.intent}")
                    
                    async for event in app.astream(state.model_dump(), stream_mode="updates"):
                        for node_name, state_diff in event.items():
                            serialized_diff = safe_serialize(state_diff)
                            # Remove heavy/redundant fields if necessary, but keep it complete for debug
                            await conn.execute(
                                "INSERT INTO system_debug_trace (task_id, node_name, state_diff) VALUES ($1, $2, $3)",
                                msg_id, node_name, json.dumps(serialized_diff)
                            )
                            logger.info(f"[{node_name}] Executed.")
                            
                    # Update status at the end
                    await conn.execute("UPDATE system_tasks SET status = 'RESULT_OUTPUT' WHERE message_id = $1", msg_id)
                    
        except Exception as e:
            logger.error(f"Worker error: {e}")
            
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(run_worker())
