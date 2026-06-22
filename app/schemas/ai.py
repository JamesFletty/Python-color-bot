"""AI route request/response schemas (v2)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.formula import FormulaResponse


class AIParseRequest(BaseModel):
    user_input: str = Field(..., max_length=4000)
    color_line: str
    line_id: int
    canonical_key: str


class ParsedRequest(BaseModel):
    shade: str
    current_level: Optional[float] = Field(None, ge=1, le=12)
    desired_level: Optional[float] = Field(None, ge=1, le=12)
    gray_percent: float = Field(0, ge=0, le=100)
    porosity: int = Field(5, ge=1, le=10)
    elasticity: int = Field(6, ge=1, le=10)
    texture: Literal["fine", "medium", "coarse"] = "medium"
    service_intent: Literal[
        "tone_deposit",
        "lift_deposit",
        "gray_coverage",
        "corrective",
        "fashion",
    ] = "tone_deposit"
    line: Optional[str] = None
    translation_notes: Optional[str] = None
    parse_source: Literal["llm", "deterministic"] = "llm"


class AITranslateRequest(BaseModel):
    source_formula: str = Field(..., max_length=4000)
    source_line: Optional[str] = None
    source_canonical_key: Optional[str] = None
    target_line: str
    target_line_id: int
    target_canonical_key: str


class AIExplainRequest(BaseModel):
    formula_result: dict[str, Any]
    user_input: str
    color_line: str
    mode: Literal["formula", "translate"] = "formula"
    translation_notes: Optional[str] = None


class ExplainResponse(BaseModel):
    summary: str


class AITranslateResponse(FormulaResponse):
    structured_request: dict[str, Any] = Field(default_factory=dict)
    translation_notes: Optional[str] = None
    parse_source: Literal["llm", "deterministic"] = "llm"
