import os
from uuid import uuid4
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
import asyncpg
from src.core.models import TaskObject
from src.api.websockets import router as ws_router

app = FastAPI(title="Agentic OS")
app.include_router(ws_router)

# Resolve DB via environment or localhost for the isolated test runner
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agenticos")

# Mount the static UI
app.mount("/ui", StaticFiles(directory="ui"), name="ui")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Agentic OS Orchestrator is running"}

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
