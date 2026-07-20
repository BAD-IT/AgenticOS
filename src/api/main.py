import os
from uuid import uuid4
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
import asyncpg
from src.core.models import TaskObject
from src.core.config import settings
from src.api.websockets import router as ws_router

app = FastAPI(title="Agentic OS")
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
async def submit_task(task: TaskObject):
    """Agnostic REST Ingress: Validates payload and pushes to PostgreSQL."""
    try:
        conn = await asyncpg.connect(DB_URL)
        msg_id = str(uuid4())
        await conn.execute(
            "INSERT INTO system_tasks (message_id, payload, status, workspace_id) VALUES ($1, $2, 'USER_INPUT', 1)",
            msg_id, task.model_dump_json()
        )
        await conn.close()
        return {"status": "accepted", "message_id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/workspaces/{workspace_id}/history")
async def get_workspace_history(workspace_id: int):
    """Fetch all tasks for a given workspace to restore UI state."""
    try:
        conn = await asyncpg.connect(DB_URL)
        rows = await conn.fetch(
            "SELECT payload, status, created_at FROM system_tasks WHERE workspace_id = $1 ORDER BY created_at ASC",
            workspace_id
        )
        await conn.close()
        
        history = []
        for r in rows:
            history.append({
                "status": r["status"],
                "payload": r["payload"]
            })
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/db/query")
async def db_query(table: str = "system_tasks", search: str = ""):
    """Read-only DB query for the WebUI Database Tab."""
    allowed_tables = ["system_tasks", "system_notifications"]
    if table not in allowed_tables:
        raise HTTPException(status_code=400, detail="Invalid table")
    try:
        conn = await asyncpg.connect(DB_URL)
        if search:
            query = f"SELECT * FROM {table} WHERE payload ILIKE $1 ORDER BY created_at DESC LIMIT 50"
            rows = await conn.fetch(query, f"%{search}%")
        else:
            query = f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT 50"
            rows = await conn.fetch(query)
        await conn.close()
        
        result = [dict(row) for row in rows]
        # Convert datetime to string for json serialization
        for r in result:
            if 'created_at' in r and r['created_at']:
                r['created_at'] = r['created_at'].isoformat()
        return {"data": result}
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
