"""Formula request/response schemas (v2 API contract)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class FormulaRequest(BaseModel):
    shade: str
    line_hint: str | None = None
    current_level: float | None = Field(None, ge=1, le=12)
    desired_level: float | None = Field(None, ge=1, le=12)
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
        "lift_and_tone",
        "gloss_refresh",
    ] = "tone_deposit"
    sub_range: str | None = None


class ShadeDetail(BaseModel):
    shade_id: int
    shade_code: str
    shade_name: Optional[str] = None
    level: Optional[float] = None
    brand: str
    product_line: str
    canonical_key: str
    normalized_tones: list[str] = Field(default_factory=list)
    sub_range: Optional[str] = None


class FormulaBlock(BaseModel):
    developer: str
    developer_rationale: Optional[str] = None
    mixing_ratio: str
    processing_time: str
    gray_coverage_guidance: Optional[str] = None
    fill_pigment_guidance: Optional[dict] = None


class HairConditions(BaseModel):
    natural_level: Optional[float] = None
    desired_level: Optional[float] = None
    gray_percent: float
    porosity: int
    elasticity: int
    texture: str


class FormulaResponse(BaseModel):
    status: Literal["ok", "caution", "blocked", "error"]
    shade: ShadeDetail
    formula: FormulaBlock
    hair_conditions: HairConditions
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    matched_rules: list[str] = Field(default_factory=list)
