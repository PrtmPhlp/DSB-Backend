"""Logging configuration module providing colored and formatted logging setup."""
import logging
import sys

import coloredlogs


def setup_logger(name: str, level=None) -> logging.Logger:
    """
    Sets up and returns a configured logger.

    :param name: Name of the logger (usually __name__).
    :param level: Logging level, default is None (will use INFO).
    :return: Configured logger.

    Example usage:
        # Basic usage with default INFO level
        logger = setup_logger(__name__)
        logger.info("This is an info message")

        # With DEBUG level
        logger = setup_logger(__name__, logging.DEBUG)
        logger.debug("This is a debug message")

        # With verbose flag from args
        logger = setup_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)
    """
    logger = logging.getLogger(name)

    # Set default level if none provided
    if level is None:
        level = logging.INFO

    # Set the logger level
    logger.setLevel(level)

    # Important: Allow the logger to propagate to the root logger
    logger.propagate = True

    # Configure coloredlogs
    coloredlogs.install(
        logger=logger,
        fmt="%(asctime)s - %(filename)s - %(levelname)s - \033[94m%(message)s\033[0m",
        datefmt="%H:%M:%S",
        level=level,
    )

    #! Logs show duplicate lines in Docker
    # Add stdout handler if needed
    # if not sys.stdout.isatty():
    #     handler = logging.StreamHandler(sys.stdout)
    #     handler.setLevel(level)  # Set handler level too
    #     logger.addHandler(handler)

    return logger
