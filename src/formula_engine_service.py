"""Shared formula engine execution for CLI and HTTP entry points."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from src.formula_builder import build_formula
from src.logging_utils import configure_logging, log_transformation
from src.paths import DEFAULT_DB_PATH


PatchTestStatus = Literal["passed", "failed", "declined", "unknown"]
TERMINAL_STATUSES = frozenset({"ok", "caution"})


def parse_sub_ranges(raw_values: list[str] | None) -> list[str]:
    """Expand comma-separated sub-range values into a flat list."""
    if not raw_values:
        return []
    parsed: list[str] = []
    for value in raw_values:
        for part in value.split(","):
            cleaned = part.strip()
            if cleaned:
                parsed.append(cleaned)
    return parsed


@dataclass
class FormulaEngineRequest:
    shade: str
    gray: float | None = None
    current_level: float | None = None
    existing_level: float | None = None
    line: str | None = None
    service_intent: str = "tone_deposit"
    desired_level: float | None = None
    patch_test_status: PatchTestStatus = "passed"
    porosity: int = 5
    sub_ranges: list[str] = field(default_factory=list)
    db_path: Path = DEFAULT_DB_PATH


def build_intake(request: FormulaEngineRequest) -> dict[str, Any]:
    intake: dict[str, Any] = {
        "service_intent": request.service_intent,
        "patch_test_status": request.patch_test_status,
        "porosity": request.porosity,
    }
    if request.sub_ranges:
        intake["selected_sub_ranges"] = list(request.sub_ranges)
    if request.current_level is not None:
        intake["natural_level"] = request.current_level
    if request.existing_level is not None:
        intake["existing_level"] = request.existing_level
    if request.desired_level is not None:
        intake["desired_level"] = request.desired_level
    return intake


def run_formula_engine(request: FormulaEngineRequest) -> dict[str, Any]:
    """Build a formula document using the Phase 1 SQLite engine."""
    if not request.db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {request.db_path}. Run init_db.py first."
        )

    logger = configure_logging()
    log_transformation(
        logger,
        "formula_request",
        {
            "shade": request.shade,
            "gray_percent": request.gray,
            "current_level": request.current_level,
            "line_hint": request.line,
            "sub_ranges": request.sub_ranges,
        },
    )

    conn = sqlite3.connect(request.db_path)
    try:
        return build_formula(
            conn,
            shade_ref=request.shade,
            gray_percent=request.gray,
            current_level=request.current_level,
            product_line_hint=request.line,
            intake=build_intake(request),
            logger=logger,
        )
    finally:
        conn.close()


def http_status_for_formula(formula: dict[str, Any]) -> int:
    """Map formula status to an HTTP status code."""
    status = formula.get("status")
    if status in TERMINAL_STATUSES:
        return 200
    if status == "error":
        return 404
    if status in {"blocked", "requires_consultation"}:
        return 422
    return 400
