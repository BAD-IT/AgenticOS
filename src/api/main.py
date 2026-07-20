import os
from uuid import uuid4
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from src.memory.database import get_db_pool
import asyncpg
from src.core.models import TaskObject
from src.core.config import settings
from src.core.logging_config import api_logger
from src.api.websockets import router as ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await get_db_pool(settings.DATABASE_URL)
    yield
    await app.state.pool.close()

api_logger.info("Initializing Agentic OS FastAPI Orchestrator")
app = FastAPI(title="Agentic OS", lifespan=lifespan)
app.include_router(ws_router)

# Resolve DB via central settings
DB_URL = settings.DATABASE_URL

# Mount the static UI
app.mount("/ui", StaticFiles(directory="ui"), name="ui")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Agentic OS Orchestrator is running"}

@app.get("/api/v1/settings")
def get_settings():
    """Returns the current active configuration for the WebUI."""
    return {
        "LLM_MODEL": settings.LLM_MODEL,
        "OLLAMA_API_BASE": settings.OLLAMA_API_BASE,
        "DATABASE_URL": settings.DATABASE_URL.replace(settings.DATABASE_URL.split('@')[0].split('//')[1], "****:****"),
        "INBOX_DIR": settings.INBOX_DIR,
        "OUTBOX_DIR": settings.OUTBOX_DIR
    }

@app.post("/api/v1/tasks/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_task(task: TaskObject, request: Request):
    """Agnostic REST Ingress: Validates payload and pushes to PostgreSQL."""
    try:
        async with request.app.state.pool.acquire() as conn:
            msg_id = str(uuid4())
            await conn.execute(
                "INSERT INTO system_tasks (message_id, payload, status, workspace_id) VALUES ($1, $2, 'USER_INPUT', 1)",
                msg_id, task.model_dump_json()
            )
            return {"status": "accepted", "message_id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/workspaces/{workspace_id}/history")
async def get_workspace_history(workspace_id: int, request: Request):
    """Fetch all tasks for a given workspace to restore UI state."""
    try:
        async with request.app.state.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT payload, status, created_at FROM system_tasks WHERE workspace_id = $1 ORDER BY created_at ASC",
                workspace_id
            )
        
        history = []
        for r in rows:
            history.append({
                "status": r["status"],
                "payload": r["payload"]
            })
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/debug/traces/{workspace_id}")
async def get_debug_traces(workspace_id: int, request: Request):
    """Fetch chronological debug traces for a given workspace."""
    try:
        async with request.app.state.pool.acquire() as conn:
            query = """
                SELECT t.id, t.task_id, t.node_name, t.state_diff, t.created_at, st.payload
                FROM system_debug_trace t
                JOIN system_tasks st ON t.task_id = st.message_id
                WHERE st.workspace_id = $1
                ORDER BY t.created_at ASC
            """
            rows = await conn.fetch(query, workspace_id)
            
            traces = []
            for r in rows:
                traces.append({
                    "id": r["id"],
                    "task_id": r["task_id"],
                    "node_name": r["node_name"],
                    "state_diff": r["state_diff"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None
                })
            return {"traces": traces}
    except Exception as e:
        api_logger.error(f"Error fetching traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/db/query")
async def db_query(request: Request, table: str = "system_tasks", search: str = ""):
    """Read-only DB query for the WebUI Database Tab."""
    allowed_tables = ["system_tasks", "system_notifications"]
    if table not in allowed_tables:
        raise HTTPException(status_code=400, detail="Invalid table")
    try:
        async with request.app.state.pool.acquire() as conn:
            if search:
                query = f"SELECT * FROM {table} WHERE payload ILIKE $1 ORDER BY created_at DESC LIMIT 50"
                rows = await conn.fetch(query, f"%{search}%")
            else:
                query = f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT 50"
                rows = await conn.fetch(query)
        
        result = [dict(row) for row in rows]
        # Convert datetime to string for json serialization
        for r in result:
            if 'created_at' in r and r['created_at']:
                r['created_at'] = r['created_at'].isoformat()
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/telemetry/queues")
async def get_telemetry_queues(request: Request):
    """Fetch raw counts for all system_tasks statuses."""
    try:
        async with request.app.state.pool.acquire() as conn:
            rows = await conn.fetch("SELECT status, COUNT(*) FROM system_tasks GROUP BY status")
        counts = {r['status']: r['count'] for r in rows}
        return {"queues": counts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/workspace/files")
def get_workspace_files():
    """List files in the inbox and outbox for the Explorer."""
    import os
    def list_files(directory):
        files = []
        if os.path.exists(directory):
            for root, _, filenames in os.walk(directory):
                for f in filenames:
                    if f.startswith('.'): continue
                    rel_dir = os.path.relpath(root, directory)
                    if rel_dir == '.': rel_dir = ''
                    files.append(os.path.join(rel_dir, f) if rel_dir else f)
        return files
    
    return {
        "inbox": list_files(settings.INBOX_DIR),
        "outbox": list_files(settings.OUTBOX_DIR)
    }
