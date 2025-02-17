#!/usr/bin/env python3
# -----------------------------------------------------------
"""
Logging setup module providing a colored logger via coloredlogs.

Usage:
    from logger_setup import LoggerSetup
    logger = LoggerSetup.setup_logger(__name__)
"""

import logging
import coloredlogs


class LoggerSetup:
    """
    A helper class to configure Python logging with colored logs.
    """

    @staticmethod
    def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
        """
        Sets up and returns a configured logger.

        Args:
            name (str): Name of the logger (usually __name__).
            level (int): Logging level (DEBUG, INFO, etc.). Default is INFO.

        Returns:
            logging.Logger: A configured logger instance.
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Prevent adding multiple handlers if already set
        if not logger.handlers:
            coloredlogs.install(
                level=level,
                logger=logger,
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S",
            )
        return logger
