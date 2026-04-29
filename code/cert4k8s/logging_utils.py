"""Logging helpers."""

import logging


def configure_logging() -> None:
    """Configure timestamped stdout logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
