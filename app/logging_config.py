"""Centralised logging configuration."""

from __future__ import annotations

import logging
import os


def configure_logging(default_level: str = "INFO") -> None:
    raw_level = os.getenv("GMX_LOG_LEVEL")
    if raw_level:
        lookup_key = raw_level.strip().upper()
        log_level = getattr(logging, lookup_key, logging.INFO)
    else:
        log_level = getattr(logging, default_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
