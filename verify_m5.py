import asyncio
import httpx
import websockets
import json
import uvicorn
from multiprocessing import Process
import time
import asyncpg
import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agenticos")

def run_server():
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8080, log_level="error")

async def test_ingress():
    print("\n--- Test 1: Ingress (Valid Payload) ---")
    async with httpx.AsyncClient() as client:
        payload = {
            "task_id": "test_123",
            "intent": "analyze logs",
            "parameters": {}
        }
        res = await client.post("http://127.0.0.1:8000/api/v1/tasks/submit", json=payload)
        print(f"Ingress Response Status: {res.status_code}")
        assert res.status_code == 202
        
        # Verify DB insertion
        conn = await asyncpg.connect(DB_URL)
        row = await conn.fetchrow("SELECT * FROM user_input_queue ORDER BY created_at DESC LIMIT 1")
        print(f"DB Inserted Payload: {row['payload']}")
        assert "analyze logs" in row['payload']
        await conn.close()

async def test_validation():
    print("\n--- Test 2: Validation (Malformed Payload) ---")
    async with httpx.AsyncClient() as client:
        payload = {
            "task_id": "test_bad",
            # missing intent
            "parameters": "string instead of dict"
        }
        res = await client.post("http://127.0.0.1:8000/api/v1/tasks/submit", json=payload)
        print(f"Validation Response Status: {res.status_code}")
        assert res.status_code == 422

async def test_telemetry():
    print("\n--- Test 3: Telemetry (WebSocket Stream) ---")
    uri = "ws://127.0.0.1:8000/api/v1/stream/notifications"
    async with websockets.connect(uri) as websocket:
        msg = await websocket.recv()
        data = json.loads(msg)
        print(f"Received WS Message: {data}")
        assert data["level"] == "info"
        assert "Log event" in data["message"]
        print("SUCCESS: Stream received correctly.")

if __name__ == "__main__":
    asyncio.run(test_ingress())
    asyncio.run(test_validation())
    asyncio.run(test_telemetry())
    print("\nSUCCESS: All M5 API and WebSockets validations passed!")
