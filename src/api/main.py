import os
from uuid import uuid4
from fastapi import FastAPI, HTTPException, status
import asyncpg
from src.core.models import TaskObject
from src.api.websockets import router as ws_router

app = FastAPI(title="Agentic OS")
app.include_router(ws_router)

# Resolve DB via environment or localhost for the isolated test runner
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agenticos")

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
            "INSERT INTO user_input_queue (message_id, payload) VALUES ($1, $2)",
            msg_id, task.model_dump_json()
        )
        await conn.close()
        return {"status": "accepted", "message_id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
