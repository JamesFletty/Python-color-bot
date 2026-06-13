"""Structured transformation logging for the Phase 1 engine."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure root logger and return the engine logger."""
    logging.basicConfig(level=level, format=_LOG_FORMAT, stream=sys.stderr)
    return logging.getLogger("hair_color_engine")


def log_transformation(
    logger: logging.Logger,
    step: str,
    details: dict[str, Any],
) -> None:
    """Log a deterministic transformation with structured context."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": step,
        **details,
    }
    logger.info("%s | %s", step, json.dumps(payload, default=str))


def log_event(logger: logging.Logger, event: str, **kwargs: Any) -> None:
    """Log a simple engine event."""
    log_transformation(logger, event, kwargs)
