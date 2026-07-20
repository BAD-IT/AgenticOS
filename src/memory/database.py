import asyncpg
from src.core.logging_config import database_logger as logger

async def get_db_pool(dsn: str) -> asyncpg.Pool:
    """
    Initialize the connection pool to PostgreSQL.
    """
    pool = await asyncpg.create_pool(dsn)
    return pool

async def init_db(pool: asyncpg.Pool):
    """
    Initialize database extensions and rely on init.sql for tables.
    """
    async with pool.acquire() as conn:
        # Enable pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        logger.info("Database initialized with pgvector. Tables are managed by init.sql.")
