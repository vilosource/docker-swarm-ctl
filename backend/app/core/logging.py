import logging
from app.core.logging_config import setup_logging

# Use centralized logging configuration
setup_logging()

# Create logger for this module
logger = logging.getLogger("docker_control_platform")