"""Pydantic schemas for the formula engine HTTP API."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class FormulaRequest(BaseModel):
    shade: str = Field(..., description='Shade reference (e.g. "Wella 7/1" or "Matrix::SoColor::5N")')
    gray: float | None = Field(None, ge=0, le=100)
    current_level: float | None = Field(None, ge=1, le=12)
    existing_level: float | None = Field(None, ge=1, le=12)
    line: str | None = Field(None, description="Product line hint when shade code is ambiguous")
    service_intent: str = "tone_deposit"
    desired_level: float | None = Field(None, ge=1, le=12)
    patch_test_status: Literal["passed", "failed", "declined", "unknown"] = "passed"
    porosity: int = Field(5, ge=1, le=10)
    elasticity: int = Field(6, ge=1, le=10)
    texture: Literal["fine", "medium", "coarse"] = "medium"
    desired_result: str = "formula recommendation"
    recommendation_type: Literal["safest", "fastest", "gray_coverage", "fashion"] = "safest"
    persist: bool = False
    sub_ranges: list[str] | None = Field(
        None,
        description="Override Stage 13 collection rules; omitted values infer from shade record",
    )

    def to_engine_request(self, db_path=None):
        from pathlib import Path

        from src.formula_engine_service import FormulaEngineRequest
        from src.paths import DEFAULT_DB_PATH

        return FormulaEngineRequest(
            shade=self.shade,
            gray=self.gray,
            current_level=self.current_level,
            existing_level=self.existing_level,
            line=self.line,
            service_intent=self.service_intent,
            desired_level=self.desired_level,
            patch_test_status=self.patch_test_status,
            porosity=self.porosity,
            sub_ranges=list(self.sub_ranges or []),
            db_path=Path(db_path) if db_path else DEFAULT_DB_PATH,
        )


class HealthResponse(BaseModel):
    status: str
    backend: str = "sqlite"
    database_path: str
    database_ready: bool
    database_url_configured: bool | None = None
    pg_db_connected: bool | None = None
    stage12_shade_count: int | None = None
    stage12_ready: bool | None = None
    stage13_rule_count: int | None = None
    stage13_ready: bool | None = None


# ── AI layer schemas ─────────────────────────────────────────────────────────

class AIFormulaRequest(BaseModel):
    user_input: str = Field(..., description="Natural-language description of client and desired result")
    color_line: str = Field(..., description="Target product line name (e.g. 'Koleston Perfect')")
    line_id: int = Field(..., description="Product line ID from /api/brands")
    canonical_key: str = Field(..., description="Canonical key for the line")


class AITranslateRequest(BaseModel):
    source_formula: str = Field(..., description="Existing formula to translate (free text)")
    source_line: str | None = Field(None, description="Source product line name (optional if in formula)")
    target_line: str = Field(..., description="Target product line name")
    target_line_id: int = Field(..., description="Target line ID")
    target_canonical_key: str = Field(..., description="Canonical key for target line")


class AIFormulaResponse(BaseModel):
    formula: dict[str, Any]
    ai_explanation: str
    structured_request: dict[str, Any]
    translation_notes: str | None = None
    ai_provider: str | None = None
    status: str = "ok"
