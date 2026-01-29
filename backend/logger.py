#ZamudioScrobbler/backend/logger.py
import logging

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s"
    )
    return logging.getLogger("vinyl")

logger = setup_logger()
