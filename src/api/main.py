import asyncio
import json
import re
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
from src.core.worker import run_worker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await get_db_pool(settings.DATABASE_URL)
    # Launch the cognitive worker as a background task in the same event loop
    worker_task = asyncio.create_task(run_worker())
    api_logger.info("Background worker started inside orchestrator process.")
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await app.state.pool.close()

api_logger.info("Initializing Agentic OS FastAPI Orchestrator")
app = FastAPI(title="Agentic OS", lifespan=lifespan)
app.include_router(ws_router)

# Resolve DB via central settings
DB_URL = settings.DATABASE_URL

# --- API Key Authentication Middleware ---
class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Skip auth if no API key is configured
        if not settings.API_KEY:
            return await call_next(request)
        # Skip auth for static files, root, and WebSocket upgrades
        path = request.url.path
        if path.startswith("/ui") or path == "/" or path == "/docs" or path == "/openapi.json":
            return await call_next(request)
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)
        # Check API key
        provided_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if provided_key != settings.API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
        return await call_next(request)

app.add_middleware(APIKeyMiddleware)

# Mount the static UI
app.mount("/ui", StaticFiles(directory="ui"), name="ui")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Agentic OS Orchestrator is running"}

@app.get("/api/v1/health")
async def health_check(request: Request):
    """Liveness & readiness probe for Docker healthcheck and monitoring."""
    try:
        async with request.app.state.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "db": "connected"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "db": str(e)})

@app.get("/api/v1/settings")
def get_settings():
    """Returns the current active configuration for the WebUI."""
    return {
        "LLM_MODEL": settings.LLM_MODEL,
        "OLLAMA_API_BASE": settings.OLLAMA_API_BASE,
        "DATABASE_URL": re.sub(r'://[^@]+@', '://****:****@', settings.DATABASE_URL),
        "INBOX_DIR": settings.INBOX_DIR,
        "OUTBOX_DIR": settings.OUTBOX_DIR
    }

BLOCKED_PATTERNS = [
    "ignore previous instructions", "ignore all instructions",
    "system prompt", "reveal your prompt", "bypass security",
    "DROP TABLE", "DELETE FROM", "; --", "' OR 1=1",
]

def check_security_guardrails(text: str) -> str:
    """Returns a rejection reason if the input matches blocked patterns, else empty string."""
    text_lower = text.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in text_lower:
            return f"Input blocked: matches security filter '{pattern}'"
    return ""

@app.post("/api/v1/tasks/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_task(task: TaskObject, request: Request, workspace_id: int = 1, priority: str = "NORMAL", webhook_url: str = None, parent_task_id: str = None):
    """Agnostic REST Ingress: Validates payload, checks security, and pushes to PostgreSQL."""
    valid_priorities = ("URGENT", "NORMAL", "LOW")
    if priority.upper() not in valid_priorities:
        raise HTTPException(status_code=400, detail=f"Invalid priority. Must be one of: {valid_priorities}")
    
    # Semantic security guardrails
    rejection = check_security_guardrails(task.intent)
    if rejection:
        raise HTTPException(status_code=422, detail=rejection)
    
    try:
        async with request.app.state.pool.acquire() as conn:
            msg_id = str(uuid4())
            await conn.execute(
                "INSERT INTO system_tasks (message_id, payload, status, workspace_id, priority, webhook_url, parent_task_id) VALUES ($1, $2, 'USER_INPUT', $3, $4, $5, $6)",
                msg_id, task.model_dump_json(), workspace_id, priority.upper(), webhook_url, parent_task_id
            )
            return {"status": "accepted", "message_id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/tasks/{message_id}/cancel")
async def cancel_task(message_id: str, request: Request):
    """Cancel a pending or in-progress task."""
    try:
        async with request.app.state.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT status FROM system_tasks WHERE message_id = $1", message_id)
            if not row:
                raise HTTPException(status_code=404, detail="Task not found")
            if row['status'] in ('RESULT_OUTPUT', 'ERROR'):
                raise HTTPException(status_code=409, detail=f"Task already finished (status: {row['status']})")
            await conn.execute(
                "UPDATE system_tasks SET status = 'ERROR', payload = payload || $2::jsonb WHERE message_id = $1",
                message_id, json.dumps({"response": "Task cancelled by user."})
            )
        return {"status": "cancelled", "message_id": message_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/tasks/{message_id}/clarify")
async def clarify_task(message_id: str, request: Request):
    """Resume a task that is waiting for user clarification."""
    try:
        body = await request.json()
        answer = body.get("answer", "")
        if not answer:
            raise HTTPException(status_code=400, detail="answer is required")
        
        async with request.app.state.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM system_tasks WHERE message_id = $1", message_id
            )
            if not row:
                raise HTTPException(status_code=404, detail="Task not found")
            if row['status'] != 'REQUIRES_CLARIFICATION':
                raise HTTPException(status_code=409, detail=f"Task is not awaiting clarification (status: {row['status']})")
            
            await conn.execute(
                "UPDATE system_tasks SET status = 'USER_INPUT', payload = payload || $2::jsonb WHERE message_id = $1",
                message_id, json.dumps({"clarification_answer": answer, "intent": answer})
            )
        return {"status": "resumed", "message_id": message_id}
    except HTTPException:
        raise
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
                query = f"SELECT * FROM {table} WHERE payload::text ILIKE $1 ORDER BY created_at DESC LIMIT 50"
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

@app.get("/api/v1/tools")
def list_tools():
    """List all registered agent tools from the plugin registry."""
    import src.graph.workflow  # noqa: F401 — ensures TOOLS_MAP is bulk-registered
    from src.tools.registry import tool_registry
    return {"tools": tool_registry.list_tools()}

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
