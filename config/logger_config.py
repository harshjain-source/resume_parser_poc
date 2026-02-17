import logging
import os
import sys

def get_logger(name, log_file=None):
    """
    Creates a logger with console and optional file handling.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # If the logger already has handlers, don't add more (avoid duplicates)
    if logger.handlers:
        return logger

    # Console Handler (Show essential info to developer)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s] : %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler (Deep debug info preserved on disk)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
