import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[logfire_handler],
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__) 