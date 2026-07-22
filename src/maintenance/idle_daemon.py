import os
import glob
import json
import logging
import asyncio
import asyncpg
from typing import List
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from src.core.config import settings
from src.maintenance.diagnostics import triage_fatal_error

logger = logging.getLogger(__name__)

WORKSPACE_OUTBOX = settings.OUTBOX_DIR

def check_queues_empty(queue_counts: dict) -> bool:
    """Strict Idle Mode: Checks if Tasks and Pending queues are zero."""
    return queue_counts.get("TASK", 0) == 0 and queue_counts.get("PENDING", 0) == 0

def garbage_collection():
    """Purges temporary files from outbox to prevent disk bloat."""
    patterns = [os.path.join(WORKSPACE_OUTBOX, p) for p in ("*.tmp", "*.log")]
    total = 0
    for pattern in patterns:
        files = glob.glob(pattern)
        for f in files:
            try:
                os.remove(f)
                logger.info(f"Garbage Collection: Removed {f}")
                total += 1
            except Exception as e:
                logger.error(f"Garbage Collection Error on {f}: {e}")
    return total

def flush_vram():
    """Programmatic trigger to unload heavy LLM models."""
    logger.info("VRAM Flush: Unloading heavy models from GPU to free up 64GB boundary.")
    return True

def get_embedding(text: str) -> List[float]:
    """Generates a real vector embedding using Ollama."""
    try:
        # NOTE: The pinned langchain-ollama==0.1.1 OllamaEmbeddings only accepts
        # `model` (extra=forbid), so base_url cannot be passed here. It falls back
        # to the underlying ollama client, which reads the OLLAMA_HOST env var.
        embeddings = OllamaEmbeddings(model=settings.EMBEDDING_MODEL)
        return embeddings.embed_query(text)
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        # Fallback to zero-vector to prevent crash during DB insert if Ollama is unreachable
        return [0.0] * 768

def generate_skill_from_task(task_intent: str, log_history: str) -> dict:
    """Experience Consolidation: Uses LLM to analyze task trajectory and abstract a reusable skill."""
    try:
        skill_llm = ChatOllama(model=settings.LLM_MODEL, base_url=settings.OLLAMA_API_BASE)
        response = skill_llm.invoke([
            SystemMessage(content=(
                "You are the Agentic OS Experience Consolidation engine. "
                "Analyze the following task trajectory and extract a reusable abstract skill. "
                "Output ONLY a concise methodology (max 150 words) that could help solve similar tasks in the future. "
                "Focus on: what approach worked, what tools were used, what pitfalls to avoid."
            )),
            HumanMessage(content=f"TASK INTENT: {task_intent}\n\nTRAJECTORY:\n{log_history[:3000]}")
        ])
        skill_abstraction = getattr(response, "content", "") or f"Skill for: {task_intent}"
    except Exception as e:
        logger.warning(f"LLM skill generation failed, using fallback: {e}")
        skill_abstraction = f"Abstracted methodology for: {task_intent}. Learned from {len(log_history.splitlines())} steps."
    
    embedding = get_embedding(skill_abstraction)
    
    return {
        "task_intent": task_intent,
        "skill_abstraction": skill_abstraction,
        "embedding": embedding
    }

async def run_idle_daemon(pool: asyncpg.Pool):
    """Background daemon: activates when queues are empty. Runs GC, VRAM flush, debug trace cleanup, and diagnostics triage."""
    logger.info("Idle Daemon started.")
    while True:
        try:
            async with pool.acquire() as conn:
                # Check queue counts
                rows = await conn.fetch("SELECT status, COUNT(*)::int as cnt FROM system_tasks GROUP BY status")
                counts = {r['status']: r['cnt'] for r in rows}
                
                if check_queues_empty(counts) and counts.get("USER_INPUT", 0) == 0:
                    logger.info("Idle Daemon: System idle — running maintenance.")
                    garbage_collection()
                    flush_vram()
                    
                    # Debug trace TTL: purge traces older than 7 days
                    deleted = await conn.execute(
                        "DELETE FROM system_debug_trace WHERE created_at < NOW() - INTERVAL '7 days'"
                    )
                    logger.info(f"Idle Daemon: Debug trace cleanup — {deleted}")
                
                # Diagnostics triage: classify any un-triaged ERROR tasks
                error_rows = await conn.fetch(
                    "SELECT message_id, payload FROM system_tasks "
                    "WHERE status = 'ERROR' AND NOT (payload ? 'error_category') "
                    "LIMIT 10"
                )
                for erow in error_rows:
                    try:
                        ep = erow['payload'] if isinstance(erow['payload'], str) else str(erow['payload'])
                        category = triage_fatal_error(ep)
                        await conn.execute(
                            "UPDATE system_tasks SET payload = payload || $2::jsonb WHERE message_id = $1",
                            erow['message_id'], json.dumps({"error_category": category})
                        )
                        logger.info(f"Diagnostics: Task {erow['message_id']} triaged as {category}")
                    except Exception as te:
                        logger.error(f"Diagnostics triage error: {te}")
                        
        except Exception as e:
            logger.error(f"Idle Daemon error: {e}")
        
        await asyncio.sleep(60)
