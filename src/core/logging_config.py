import logging
import json
import os
import contextvars
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")

# Context variable for propagating task_id across async boundaries
current_task_id: contextvars.ContextVar[str] = contextvars.ContextVar("current_task_id", default="")

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter with automatic task_id injection."""
    def format(self, record):
        log_entry = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        task_id = getattr(record, "task_id", "") or current_task_id.get("")
        if task_id:
            log_entry["task_id"] = task_id
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)

def setup_logger(name: str, filename: str) -> logging.Logger:
    """
    Sets up a logger with a TimedRotatingFileHandler using JSON output.
    Rotates at midnight and keeps 3 days of backups.
    Also adds a StreamHandler for stdout visibility in containers.
    """
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
        
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid attaching multiple handlers if setup is called multiple times
    if not logger.handlers:
        json_fmt = JSONFormatter()

        # File handler — structured JSON logs for persistence
        log_path = os.path.join(LOG_DIR, filename)
        file_handler = TimedRotatingFileHandler(log_path, when="midnight", interval=1, backupCount=3)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(json_fmt)
        logger.addHandler(file_handler)

        # Stream handler — human-readable for docker logs
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(logging.Formatter('%(asctime)s [%(name)s] %(levelname)s %(message)s'))
        logger.addHandler(stream_handler)
        
    return logger

# Pre-configure the main system loggers
api_logger = setup_logger("api", "api.log")
orchestrator_logger = setup_logger("orchestrator", "orchestrator.log")
sandbox_logger = setup_logger("sandbox", "sandbox.log")
database_logger = setup_logger("database", "database.log")
