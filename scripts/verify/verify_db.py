import asyncio
import os
import asyncpg
from src.memory.database import get_db_pool, init_db

async def main():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agenticos")
    
    print(f"Connecting to {db_url}...")
    try:
        pool = await get_db_pool(db_url)
        await init_db(pool)
        
        async with pool.acquire() as conn:
            # Verify pgvector
            ext = await conn.fetchval("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            if ext == 'vector':
                print("SUCCESS: pgvector extension is active.")
            else:
                print("FAILED: pgvector extension not found.")
                
            # Verify tables
            tables = await conn.fetch("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';")
            table_names = [t['tablename'] for t in tables]
            print(f"Tables found: {table_names}")
            
    except Exception as e:
        print(f"Database connection or initialization failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
