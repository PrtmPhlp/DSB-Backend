# logger_setup.py
import logging
import coloredlogs


def setup_logger(name: str, level = logging.INFO) -> logging.Logger:
    """
    Sets up and returns a configured logger.

    :param name: Name of the logger (usually __name__).
    :param level: Logging level, default is INFO.
    :return: Configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    coloredlogs.install(
        logger=logger,
        fmt="%(asctime)s - %(filename)s - %(levelname)s - \033[94m%(message)s\033[0m",
        datefmt="%H:%M:%S",
        level=level,
    )
    return logger
