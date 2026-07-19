import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/api/v1/stream/notifications")
async def stream_notifications(websocket: WebSocket):
    """Semantic Terminal Feed: Streams log events to the WebUI in real-time."""
    await websocket.accept()
    try:
        # Mock streaming telemetry for M5
        for i in range(3):
            await asyncio.sleep(0.1)
            await websocket.send_text(json.dumps({"level": "info", "message": f"Log event {i}: Executing LangGraph node..."}))
    except WebSocketDisconnect:
        pass

@router.websocket("/api/v1/stream/chat")
async def stream_chat(websocket: WebSocket):
    """Interactive UI Socket: Bidirectional connection for the center panel."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            if data == "/clear":
                await websocket.send_text(json.dumps({"action": "cleared"}))
            else:
                # Mock a graph pause for clarification
                await websocket.send_text(json.dumps({"status": "REQUIRES_CLARIFICATION", "message": "Could you provide more context?"}))
    except WebSocketDisconnect:
        pass
