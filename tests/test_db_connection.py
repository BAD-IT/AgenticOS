import os
import pytest
import asyncpg

pytestmark = pytest.mark.asyncio

async def test_db_connection_and_queues():
    """Verify asyncpg can connect to the Docker agenticos_db and read tables."""
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agenticos")
    conn = await asyncpg.connect(db_url)
    
    rows = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    tables = [row["tablename"] for row in rows]
    
    expected_tables = ["system_tasks", "system_notifications", "agent_skills"]
    for table in expected_tables:
        assert table in tables, f"Expected table {table} to exist in DB"
        
    await conn.close()
