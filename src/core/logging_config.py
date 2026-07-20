import logging
import os
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")

def setup_logger(name: str, filename: str) -> logging.Logger:
    """
    Sets up a logger with a TimedRotatingFileHandler.
    Rotates at midnight and keeps 3 days of backups.
    """
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
        
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid attaching multiple handlers if setup is called multiple times
    if not logger.handlers:
        log_path = os.path.join(LOG_DIR, filename)
        handler = TimedRotatingFileHandler(log_path, when="midnight", interval=1, backupCount=3)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

# Pre-configure the main system loggers
api_logger = setup_logger("api", "api.log")
orchestrator_logger = setup_logger("orchestrator", "orchestrator.log")
sandbox_logger = setup_logger("sandbox", "sandbox.log")
database_logger = setup_logger("database", "database.log")
