# logger.py
import logging

from src.config import LOG_DIR


def setup_logger(name: str) -> logging.Logger:
    """Set up a logger with appropriate format and handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Create log directory if it doesn't exist
    log_dir = LOG_DIR
    log_dir.mkdir(exist_ok=True)

    # File handler
    file_handler = logging.FileHandler(log_dir / f"{name}.log")
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logger("obit_transcriber")
