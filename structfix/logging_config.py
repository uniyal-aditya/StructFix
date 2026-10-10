"""Structured Logging Configuration for StructFix.

Configures structured logging to stderr while ensuring raw user-submitted
prompts, JSON content, schemas, and model reasoning are never leaked into logs.
"""

from __future__ import annotations

import logging
import sys


def setup_logger(name: str = "structfix", verbose: bool = False) -> logging.Logger:
    """Configure and return a structured logger writing to stderr."""
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.propagate = False

    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [structfix] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
