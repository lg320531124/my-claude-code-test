"""Logging utilities."""

from __future__ import annotations
import logging
from pathlib import Path


def get_logger(name: str = "cc") -> logging.Logger:
    """Get configured logger."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(levelname)s: %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


def setup_file_logging(path: Path) -> None:
    """Setup file logging."""
    logger = get_logger()
    handler = logging.FileHandler(path)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)
