import os
import asyncio
import json
import asyncpg
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.core.config import settings

router = APIRouter()

@router.websocket("/api/v1/stream/notifications")
async def stream_notifications(websocket: WebSocket):
    """Semantic Terminal Feed: Streams log events to the WebUI in real-time."""
    await websocket.accept()
    conn = None
    
    async def handle_notification(connection, pid, channel, payload):
        try:
            await websocket.send_text(payload)
        except Exception:
            pass

    try:
        pool = websocket.app.state.pool
        conn = await pool.acquire()
        await conn.add_listener("system_notifications_channel", handle_notification)
        
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        pass
    finally:
        if conn:
            await conn.remove_listener("system_notifications_channel", handle_notification)
            await pool.release(conn)

@router.websocket("/api/v1/stream/chat")
async def stream_chat(websocket: WebSocket):
    """Interactive UI Socket: Bidirectional connection for the center panel."""
    await websocket.accept()
    conn = None
    
    async def handle_chat_update(connection, pid, channel, payload):
        try:
            await websocket.send_text(payload)
        except Exception:
            pass

    try:
        pool = websocket.app.state.pool
        conn = await pool.acquire()
        await conn.add_listener("system_tasks_channel", handle_chat_update)
        
        while True:
            data = await websocket.receive_text()
            if data == "/clear":
                await websocket.send_text(json.dumps({"action": "cleared"}))
            else:
                # In real scenario, we might insert the task to DB here, but UI uses REST /submit
                pass
    except WebSocketDisconnect:
        pass
    finally:
        if conn:
            await conn.remove_listener("system_tasks_channel", handle_chat_update)
            await pool.release(conn)

@router.websocket("/api/v1/stream/logs/{log_name}")
async def stream_logs(websocket: WebSocket, log_name: str):
    """Stream backend logfiles via WebSocket."""
    await websocket.accept()
    
    allowed_logs = ["api", "orchestrator", "sandbox", "database"]
    if log_name not in allowed_logs:
        await websocket.send_text("Error: Invalid log file requested.")
        await websocket.close()
        return

    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
    log_file = os.path.join(log_dir, f"{log_name}.log")
    
    # Create an empty log file if it doesn't exist
    if not os.path.exists(log_file):
        os.makedirs(log_dir, exist_ok=True)
        with open(log_file, 'w') as f:
            f.write("Log initialized.\n")
            
    try:
        with open(log_file, "r") as f:
            # Send the last 20 lines on connection
            lines = f.readlines()
            for line in lines[-20:]:
                await websocket.send_text(line)
            
            # Tail the file
            while True:
                line = f.readline()
                if line:
                    await websocket.send_text(line)
                else:
                    await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
