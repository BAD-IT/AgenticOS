import asyncpg
from src.core.models import QueueName
from src.core.logging_config import database_logger as logger

async def get_db_pool(dsn: str) -> asyncpg.Pool:
    """
    Initialize the connection pool to PostgreSQL.
    """
    pool = await asyncpg.create_pool(dsn)
    return pool

async def init_db(pool: asyncpg.Pool):
    """
    Initialize database extensions and draft tables for the 7 system queues.
    """
    async with pool.acquire() as conn:
        # Enable pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create 7 distinct tables representing the queues.
        for queue in QueueName:
            table_name = queue.value.lower()
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                message_id VARCHAR(255) PRIMARY KEY,
                payload JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
            await conn.execute(create_table_sql)
            
        logger.info("Database initialized with pgvector and all queue tables.")
