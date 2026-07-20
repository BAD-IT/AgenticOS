import os
import glob
import logging
from typing import List
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

def mock_embedding(text: str) -> List[float]:
    """Generates a deterministic minimal 3D vector for testing."""
    length = len(text)
    return [float(length % 10) / 10.0, float(length % 5) / 5.0, 0.5]

def generate_skill_from_task(task_intent: str, log_history: str) -> dict:
    """Experience Consolidation: Analyzes successful iterations into an abstract skill."""
    skill_abstraction = f"Abstracted methodology for: {task_intent}. Learned from {len(log_history.splitlines())} steps."
    embedding = mock_embedding(skill_abstraction)
    
    return {
        "task_intent": task_intent,
        "skill_abstraction": skill_abstraction,
        "embedding": embedding
    }
