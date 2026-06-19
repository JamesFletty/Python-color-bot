"""Typed domain models for the deterministic formula engine."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .production_models import FormulaZone, HairTexture, RecommendationType, RiskSeverity, RiskType


class ServiceIntent(str, Enum):
    """High-level service classification driving rule and step templates."""

    TONE_DEPOSIT = "tone_deposit"
    GRAY_COVERAGE = "gray_coverage"
    LIFT_AND_TONE = "lift_and_tone"
    CORRECTION = "correction"
    GLOSS_REFRESH = "gloss_refresh"


class RecommendationStatus(str, Enum):
    OK = "ok"
    CAUTION = "caution"
    BLOCKED = "blocked"
    REQUIRES_CONSULTATION = "requires_consultation"


class RuleScopeTier(str, Enum):
    """Applicability specificity for precedence resolution."""

    UNIVERSAL = "universal"
    BRAND = "brand"
    LINE = "line"


class SelectedShade(BaseModel):
    """Shade chosen for a formula step (from research shade catalog)."""

    shade_id: UUID
    shade_code: str
    sub_range_id: Optional[UUID] = None
    sub_range_name: Optional[str] = None
    zone: FormulaZone = FormulaZone.ALL


class EngineInput(BaseModel):
    """Normalized engine input contract."""

    consultation_id: UUID
    line_id: UUID
    brand_id: Optional[UUID] = Field(
        None,
        description="Optional stylist constraint; derived from line_id when omitted.",
    )
    line_region_id: Optional[UUID] = None

    natural_level: int = Field(..., ge=1, le=12)
    existing_level: Optional[int] = Field(None, ge=1, le=12)
    existing_artificial_color: Optional[str] = None
    porosity: int = Field(..., ge=1, le=10)
    elasticity: int = Field(..., ge=1, le=10)
    gray_percentage: int = Field(..., ge=0, le=100)
    texture: HairTexture
    desired_result: str
    desired_tone: Optional[str] = None
    desired_level: Optional[int] = Field(None, ge=1, le=12)
    service_intent: ServiceIntent

    selected_shades: list[SelectedShade] = Field(default_factory=list)
    developer_id: Optional[UUID] = None
    recommendation_type: RecommendationType = RecommendationType.SAFEST
    hair_length: Optional[str] = Field(
        None,
        description="Salon quantity planning hint: short, medium, long, or extra_long.",
    )

    model_config = ConfigDict(use_enum_values=False)


class MatchedRule(BaseModel):
    """A formulation rule that matched input conditions."""

    rule_id: UUID
    rule_name: str
    rule_priority: int
    rule_category: str
    scope_tier: RuleScopeTier
    reason: str
    evidence_status: Optional[str] = None
    evidence_notes: Optional[str] = None


class SuggestedFormulaStep(BaseModel):
    """Concrete formula step before persistence."""

    step_order: int
    zone: FormulaZone
    shade_id: Optional[UUID] = None
    shade_code: Optional[str] = None
    developer_id: Optional[UUID] = None
    developer_volume: Optional[int] = None
    mixing_ratio: Optional[str] = None
    quantity_grams: Optional[int] = Field(
        None, description="Placeholder grams when shade weight not supplied."
    )
    processing_time_minutes: int
    special_instructions: Optional[str] = None
    is_optional: bool = False


class RiskAssessmentDraft(BaseModel):
    """Risk row ready for persistence."""

    risk_type: RiskType
    probability: Decimal = Field(..., ge=0, le=1)
    severity: RiskSeverity
    contributing_factors: list[dict[str, Any]] = Field(default_factory=list)
    mitigation: str
    requires_waiver: bool = False
    waiver_text: Optional[str] = None


class PersistencePayload(BaseModel):
    """ORM-ready payloads for consultation outcome tables."""

    formula: dict[str, Any]
    formula_steps: list[dict[str, Any]]
    risk_assessments: list[dict[str, Any]]


class EngineOutput(BaseModel):
    """Structured engine result."""

    recommendation_status: RecommendationStatus
    matched_rules: list[MatchedRule] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggested_formula: list[SuggestedFormulaStep] = Field(default_factory=list)
    risk_assessments: list[RiskAssessmentDraft] = Field(default_factory=list)
    explanation_summary: str
    persistence_payload: Optional[PersistencePayload] = None
    triggered_workflows: list[str] = Field(default_factory=list)
    formula_zones: Optional[list[str]] = None
    fill_pigment_guidance: Optional[dict[str, Any]] = None
    quantity_rationale: Optional[str] = None
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)


class RuleEvaluationContext(BaseModel):
    """Flattened evaluation context built from EngineInput."""

    consultation_id: UUID
    line_id: UUID
    brand_id: Optional[UUID] = None
    line_region_id: Optional[UUID] = None
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

    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_input(cls, engine_input: EngineInput, brand_id: UUID | None) -> RuleEvaluationContext:
        existing = engine_input.existing_level if engine_input.existing_level is not None else engine_input.natural_level
        desired = engine_input.desired_level if engine_input.desired_level is not None else existing
        level_delta = desired - existing
        lift = max(0, level_delta)
        deposit = max(0, -level_delta)
        return cls(
            consultation_id=engine_input.consultation_id,
            line_id=engine_input.line_id,
            brand_id=brand_id,
            line_region_id=engine_input.line_region_id,
            natural_level=engine_input.natural_level,
            existing_level=engine_input.existing_level,
            existing_artificial_color=engine_input.existing_artificial_color,
            porosity=engine_input.porosity,
            elasticity=engine_input.elasticity,
            gray_percentage=engine_input.gray_percentage,
            texture=engine_input.texture.value,
            desired_result=engine_input.desired_result,
            desired_tone=engine_input.desired_tone,
            desired_level=engine_input.desired_level,
            service_intent=engine_input.service_intent.value,
            lift_levels=lift,
            deposit_levels=deposit,
            level_delta=level_delta,
        )


class AccumulatedActions(BaseModel):
    """Mutable action state while applying matched rules in precedence order."""

    developer_volume: Optional[int] = None
    developer_locked: bool = False
    mixing_ratio: Optional[str] = None
    recommendation_status: Optional[RecommendationStatus] = None
    block_reason: Optional[str] = None
    require_natural_shade_mix: bool = False
    natural_shade_ratio: float = 0.0
    processing_time_minutes: int = 35
    processing_time_adjustments: list[str] = Field(default_factory=list)
    extra_steps: list[SuggestedFormulaStep] = Field(default_factory=list)
    risk_modifiers: dict[str, float] = Field(default_factory=dict)
    triggered_workflows: list[str] = Field(default_factory=list)
    hard_stops: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    require_fill_pigment: bool = False
    fill_pigment_guidance: dict[str, Any] | None = None
    deposit_levels: int = 0

    def apply_risk_modifier(self, modifiers: dict[str, float]) -> None:
        for key, delta in modifiers.items():
            self.risk_modifiers[key] = self.risk_modifiers.get(key, 0.0) + delta
