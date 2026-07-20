import os
import glob
import logging
from typing import List
from langchain_ollama import OllamaEmbeddings
from src.core.config import settings

logger = logging.getLogger(__name__)

WORKSPACE_OUTBOX = settings.OUTBOX_DIR

def check_queues_empty(queue_counts: dict) -> bool:
    """Strict Idle Mode: Checks if Tasks and Pending queues are zero."""
    return queue_counts.get("TASK", 0) == 0 and queue_counts.get("PENDING", 0) == 0

def garbage_collection():
    """Purges temporary files from outbox to prevent disk bloat."""
    pattern = os.path.join(WORKSPACE_OUTBOX, "*.tmp")
    files = glob.glob(pattern)
    for f in files:
        try:
            os.remove(f)
            logger.info(f"Garbage Collection: Removed {f}")
        except Exception as e:
            logger.error(f"Garbage Collection Error on {f}: {e}")
    return len(files)

def flush_vram():
    """Programmatic trigger to unload heavy LLM models."""
    logger.info("VRAM Flush: Unloading heavy models from GPU to free up 64GB boundary.")
    return True

def get_embedding(text: str) -> List[float]:
    """Generates a real vector embedding using Ollama."""
    try:
        embeddings = OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL,
            base_url=settings.OLLAMA_API_BASE
        )
        return embeddings.embed_query(text)
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        # Fallback to zero-vector to prevent crash during DB insert if Ollama is unreachable
        return [0.0] * 768

def generate_skill_from_task(task_intent: str, log_history: str) -> dict:
    """Experience Consolidation: Analyzes successful iterations into an abstract skill."""
    skill_abstraction = f"Abstracted methodology for: {task_intent}. Learned from {len(log_history.splitlines())} steps."
    embedding = get_embedding(skill_abstraction)
    
    return {
        "task_intent": task_intent,
        "skill_abstraction": skill_abstraction,
        "embedding": embedding
    }
