import os
import asyncio
import json
import asyncpg
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.core.config import settings

router = APIRouter()
DB_URL = settings.DATABASE_URL

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
        conn = await asyncpg.connect(DB_URL)
        await conn.add_listener("system_notifications_channel", handle_notification)
        
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        pass
    finally:
        if conn:
            await conn.remove_listener("system_notifications_channel", handle_notification)
            await conn.close()

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
        conn = await asyncpg.connect(DB_URL)
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
            await conn.close()
