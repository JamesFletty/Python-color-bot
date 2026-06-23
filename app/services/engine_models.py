"""Typed domain models for the v2 deterministic formula engine."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ServiceIntent(str, Enum):
    TONE_DEPOSIT = "tone_deposit"
    GRAY_COVERAGE = "gray_coverage"
    LIFT_DEPOSIT = "lift_deposit"
    LIFT_AND_TONE = "lift_and_tone"
    CORRECTIVE = "corrective"
    CORRECTION = "corrective"
    FASHION = "fashion"
    GLOSS_REFRESH = "gloss_refresh"


class RecommendationStatus(str, Enum):
    OK = "ok"
    CAUTION = "caution"
    BLOCKED = "blocked"
    REQUIRES_CONSULTATION = "requires_consultation"


class RuleScopeTier(str, Enum):
    UNIVERSAL = "universal"
    BRAND = "brand"
    LINE = "line"


class MatchedRule(BaseModel):
    rule_id: str
    rule_name: str
    rule_priority: int
    rule_category: str
    scope_tier: RuleScopeTier
    reason: str
    evidence_status: Optional[str] = None


class RuleEvaluationContext(BaseModel):
    consultation_id: UUID
    line_id: int
    brand_id: Optional[int] = None
    natural_level: int
    existing_level: Optional[int] = None
    existing_artificial_color: Optional[str] = None
    porosity: int
    elasticity: int
    gray_percentage: int
    texture: str
    desired_result: str
    desired_tone: Optional[str] = None
    desired_level: Optional[int] = None
    service_intent: str
    lift_levels: int = 0
    deposit_levels: int = 0
    level_delta: int = 0
    selected_sub_ranges: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_request(
        cls,
        *,
        line_id: int,
        brand_id: int | None,
        natural_level: int | None,
        existing_level: int | None,
        desired_level: int | None,
        gray_percent: float,
        porosity: int,
        elasticity: int,
        texture: str,
        service_intent: str,
        sub_range: str | None = None,
    ) -> RuleEvaluationContext:
        natural = int(natural_level or existing_level or 5)
        existing = int(existing_level if existing_level is not None else natural)
        desired = int(desired_level if desired_level is not None else existing)
        level_delta = desired - existing
        sub_ranges = [sub_range] if sub_range else []
        return cls(
            consultation_id=uuid4(),
            line_id=line_id,
            brand_id=brand_id,
            natural_level=natural,
            existing_level=existing_level,
            porosity=porosity,
            elasticity=elasticity,
            gray_percentage=int(gray_percent),
            texture=texture,
            desired_result="formula request",
            desired_level=desired_level,
            service_intent=service_intent,
            lift_levels=max(0, level_delta),
            deposit_levels=max(0, -level_delta),
            level_delta=level_delta,
            selected_sub_ranges=sub_ranges,
        )


class AccumulatedActions(BaseModel):
    developer_volume: Optional[int] = None
    developer_locked: bool = False
    mixing_ratio: Optional[str] = None
    recommendation_status: Optional[RecommendationStatus] = None
    require_natural_shade_mix: bool = False
    natural_shade_ratio: float = 0.0
    processing_time_minutes: int = 35
    processing_time_adjustments: list[str] = Field(default_factory=list)
    hard_stops: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    require_fill_pigment: bool = False
    fill_pigment_guidance: dict[str, Any] | None = None
    deposit_levels: int = 0
    developer_rationale: Optional[str] = None
    gray_coverage_guidance: Optional[str] = None
    triggered_workflows: list[str] = Field(default_factory=list)
    block_reason: Optional[str] = None

    def apply_risk_modifier(self, modifiers: dict[str, float]) -> None:
        del modifiers  # v2 simplified path — risk scoring deferred to Phase 3


class ResolvedShade(BaseModel):
    shade_id: int
    shade_code: str
    shade_name: Optional[str] = None
    level: Optional[float] = None
    brand: str
    product_line: str
    line_id: int
    canonical_key: str
    sub_range: Optional[str] = None
    normalized_tones: list[str] = Field(default_factory=list)
    mixing_ratio: Optional[str] = None
    color_type: Optional[str] = None
    gray_coverage_claim: Optional[str] = None
