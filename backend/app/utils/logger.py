import logging
import sys
from app.core.config import get_settings

settings = get_settings()

# Configure logging
logger = logging.getLogger("secure_chat")
logger.setLevel(settings.LOG_LEVEL)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

def get_logger(name: str):
    return logger.getChild(name)
