# Logging from external file
import logging
from logger_setup import LoggerSetup

# -----------------------------------------------------------
# 1) Logger Setup
# -----------------------------------------------------------
logger = LoggerSetup.setup_logger(__name__, logging.DEBUG)

logger.setLevel(logging.DEBUG)
logger.debug("Hello")
logger.info("Hello")
logger.warning("Hello")
logger.error("Hello")
logger.critical("Hello")
