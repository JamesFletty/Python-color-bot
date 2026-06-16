"""Alembic revision: research-layer baseline schema for Stage 12 import.

Revision ID: research_baseline
Revises: None
Create Date: 2026-06-16
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "research_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA_PATH = Path(__file__).resolve().parent / "research_baseline_schema.sql"


def _statements(sql: str) -> list[str]:
    cleaned = re.sub(r"--[^\n]*", "", sql)
    parts = [part.strip() for part in cleaned.split(";")]
    return [part for part in parts if part]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    for statement in _statements(sql):
        if statement.upper().startswith("CREATE EXTENSION"):
            continue
        op.execute(statement + ";")


def downgrade() -> None:
    for table in (
        "issue_log",
        "record_version",
        "record_source",
        "line_developer",
        "developer",
        "line_technical_rule",
        "shade_tone_code",
        "tone_normalization",
        "tone_code_reference",
        "normalized_tone",
        "shade",
        "shade_raw",
        "source_document",
        "sub_range",
        "product_line_region",
        "product_line",
        "brand",
        "ingestion_run",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
