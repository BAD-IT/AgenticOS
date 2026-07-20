# Feature: Database Pooling Refactoring

## Goal
The Agentic OS backend currently opens a new `asyncpg` connection on every request (`await asyncpg.connect(DB_URL)`) and does not pool connections. This causes performance overhead and lacks robustness against connection limits. We will refactor the FastAPI application to utilize a global connection pool.

## Specifications
1. **Lifespan Manager:** Update `src/api/main.py` to use `@asynccontextmanager def lifespan(app: FastAPI)` to instantiate the DB pool on startup and gracefully close it on shutdown.
2. **Context Manager Usage:** Refactor all database calls to use `async with app.state.pool.acquire() as conn:`. This guarantees connections are released, preventing resource leaks.
3. **WebSocket Adjustments:** `websockets.py` endpoints must retrieve the pool from `websocket.app.state.pool`. 
4. **Cleanup:** Delete duplicated module imports in websocket endpoint bodies.
