import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:12b")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agenticos")
    OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    INBOX_DIR = os.getenv("INBOX_DIR", "workspace/inbox")
    OUTBOX_DIR = os.getenv("OUTBOX_DIR", "workspace/outbox")
    TASK_TIMEOUT_SECONDS = int(os.getenv("TASK_TIMEOUT_SECONDS", "300"))
    LLM_CALL_TIMEOUT_SECONDS = int(os.getenv("LLM_CALL_TIMEOUT_SECONDS", "120"))
    CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "5"))
    MAX_OVERSEER_RETRIES = int(os.getenv("MAX_OVERSEER_RETRIES", "2"))
    WORKER_FALLBACK_POLL_SECONDS = int(os.getenv("WORKER_FALLBACK_POLL_SECONDS", "30"))
    REVIEW_MODEL = os.getenv("REVIEW_MODEL", "")
    API_KEY = os.getenv("AGENTICOS_API_KEY", "")
    DEBUG_TRACE_TTL_DAYS = int(os.getenv("DEBUG_TRACE_TTL_DAYS", "7"))

settings = Config()
