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

settings = Config()
