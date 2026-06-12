"""Pydantic v2 schemas for the operational / production schema layer."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .production_models import (
    ColorScienceConfidence,
    ConsultationStatus,
    FormulaStatus,
    FormulaZone,
    FormulationRuleCategory,
    HairTexture,
    IntakeSource,
    IntermixEvidenceStatus,
    IntermixRestrictionType,
    IntermixRuleScope,
    RecommendationType,
    RiskSeverity,
    RiskType,
    ScalpCondition,
)


# ---------------------------------------------------------------------------
# Shared validators
# ---------------------------------------------------------------------------


def _validate_gray_percentage(v: int) -> int:
    if not 0 <= v <= 100:
        raise ValueError("gray_percentage must be between 0 and 100")
    return v


def _validate_level(v: int) -> int:
    if not 1 <= v <= 12:
        raise ValueError("level must be between 1 and 12")
    return v


def _validate_porosity_elasticity(v: int) -> int:
    if not 1 <= v <= 10:
        raise ValueError("value must be between 1 and 10")
    return v


def _validate_unit_interval(v: Decimal) -> Decimal:
    if not Decimal("0") <= v <= Decimal("1"):
        raise ValueError("value must be between 0.0 and 1.0")
    return v


# ---------------------------------------------------------------------------
# JSON helper schemas for formulation_rule
# ---------------------------------------------------------------------------


class RuleConditionPredicate(BaseModel):
    """Single predicate in a formulation rule condition tree."""

    field: str
    op: str
    value: Any

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"field": "gray_percentage", "op": ">", "value": 50}]
        }
    )


class RuleCondition(BaseModel):
    """Condition JSON shape for formulation_rule.rule_condition."""

    all_of: list[RuleConditionPredicate] = Field(default_factory=list)
    any_of: list[RuleConditionPredicate] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "all_of": [
                        {"field": "gray_percentage", "op": ">", "value": 50},
                        {"field": "natural_level", "op": "<=", "value": 6},
                    ],
                    "any_of": [{"field": "porosity", "op": ">", "value": 7}],
                }
            ]
        }
    )


class RuleActionAddStep(BaseModel):
    zone: FormulaZone
    processing_time_adjustment: Optional[str] = None


class RuleAction(BaseModel):
    """Action JSON shape for formulation_rule.rule_action."""

    set_developer_volume: Optional[int] = None
    require_natural_shade_mix: Optional[bool] = None
    natural_shade_ratio: Optional[float] = None
    add_step: Optional[RuleActionAddStep] = None
    risk_modifier: Optional[dict[str, float]] = None
    trigger_workflow: Optional[str] = None
    adjust_developer_volume_delta: Optional[int] = None
    adjust_processing_time_minutes: Optional[int] = None
    increase_risk_score: Optional[dict[str, float]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "set_developer_volume": 20,
                    "require_natural_shade_mix": True,
                    "natural_shade_ratio": 0.5,
                    "add_step": {
                        "zone": "root",
                        "processing_time_adjustment": "+10min",
                    },
                    "risk_modifier": {"gray_coverage": -0.2},
                }
            ]
        }
    )


# ---------------------------------------------------------------------------
# A. universal_color_science
# ---------------------------------------------------------------------------


class UniversalColorScienceBase(BaseModel):
    underlying_pigment: Optional[str] = None
    neutralizing_tone: Optional[str] = None
    neutralizing_tone_id: Optional[UUID] = None
    exposure_stage: Optional[str] = None
    source_label: str
    source_id: Optional[UUID] = None
    confidence: ColorScienceConfidence


class UniversalColorScienceCreate(UniversalColorScienceBase):
    level: int = Field(..., ge=1, le=12)


class UniversalColorScienceUpdate(BaseModel):
    underlying_pigment: Optional[str] = None
    neutralizing_tone: Optional[str] = None
    neutralizing_tone_id: Optional[UUID] = None
    exposure_stage: Optional[str] = None
    source_label: Optional[str] = None
    source_id: Optional[UUID] = None
    confidence: Optional[ColorScienceConfidence] = None


class UniversalColorScienceResponse(UniversalColorScienceBase):
    level: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# B. line_technical_rule (additive columns)
# ---------------------------------------------------------------------------


class LineTechnicalRuleTypedColumns(BaseModel):
    developer_volume: Optional[int] = Field(
        None,
        gt=0,
        le=100,
        description="Salon developer volume convention (e.g. 10 = 10 vol)",
    )
    max_lift_levels: Optional[Decimal] = None
    gray_coverage_pct: Optional[int] = Field(None, ge=0, le=100)
    mixing_ratio_num: Optional[int] = Field(None, gt=0)
    mixing_ratio_den: Optional[int] = Field(None, gt=0)
    processing_time_min: Optional[int] = Field(None, gt=0)
    applicable_hair_type: Optional[list[str]] = None
    porosity_adjustment: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_mixing_ratio_pair(self) -> LineTechnicalRuleTypedColumns:
        num, den = self.mixing_ratio_num, self.mixing_ratio_den
        if (num is None) != (den is None):
            raise ValueError(
                "mixing_ratio_num and mixing_ratio_den must both be set or both be null"
            )
        return self


class LineTechnicalRuleCreate(LineTechnicalRuleTypedColumns):
    line_region_id: UUID
    rule_type: str
    rule_value: Optional[dict[str, Any]] = None
    applies_to_sub_range_id: Optional[UUID] = None
    source_id: UUID


class LineTechnicalRuleUpdate(BaseModel):
    rule_type: Optional[str] = None
    rule_value: Optional[dict[str, Any]] = None
    applies_to_sub_range_id: Optional[UUID] = None
    source_id: Optional[UUID] = None
    developer_volume: Optional[int] = Field(None, gt=0, le=100)
    max_lift_levels: Optional[Decimal] = None
    gray_coverage_pct: Optional[int] = Field(None, ge=0, le=100)
    mixing_ratio_num: Optional[int] = Field(None, gt=0)
    mixing_ratio_den: Optional[int] = Field(None, gt=0)
    processing_time_min: Optional[int] = Field(None, gt=0)
    applicable_hair_type: Optional[list[str]] = None
    porosity_adjustment: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_mixing_ratio_pair(self) -> LineTechnicalRuleUpdate:
        num, den = self.mixing_ratio_num, self.mixing_ratio_den
        if (num is None) != (den is None):
            raise ValueError(
                "mixing_ratio_num and mixing_ratio_den must both be set or both be null"
            )
        return self


class LineTechnicalRuleResponse(LineTechnicalRuleTypedColumns):
    rule_id: UUID
    line_region_id: UUID
    rule_type: str
    rule_value: Optional[dict[str, Any]] = None
    applies_to_sub_range_id: Optional[UUID] = None
    source_id: UUID

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# C. shade_intermixing_rule
# ---------------------------------------------------------------------------


class ShadeIntermixingRuleBase(BaseModel):
    line_region_id: Optional[UUID] = None
    applies_to_sub_range_id: Optional[UUID] = None
    compatible_sub_range_id: Optional[UUID] = None
    shade_id: Optional[UUID] = None
    compatible_shade_id: Optional[UUID] = None
    rule_scope: IntermixRuleScope
    restriction_type: IntermixRestrictionType
    restriction_note: str
    source_id: UUID
    evidence_status: IntermixEvidenceStatus


class ShadeIntermixingRuleCreate(ShadeIntermixingRuleBase):
    pass


class ShadeIntermixingRuleUpdate(BaseModel):
    line_region_id: Optional[UUID] = None
    applies_to_sub_range_id: Optional[UUID] = None
    compatible_sub_range_id: Optional[UUID] = None
    shade_id: Optional[UUID] = None
    compatible_shade_id: Optional[UUID] = None
    rule_scope: Optional[IntermixRuleScope] = None
    restriction_type: Optional[IntermixRestrictionType] = None
    restriction_note: Optional[str] = None
    source_id: Optional[UUID] = None
    evidence_status: Optional[IntermixEvidenceStatus] = None


class ShadeIntermixingRuleResponse(ShadeIntermixingRuleBase):
    rule_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# D. formulation_rule + join tables
# ---------------------------------------------------------------------------


class FormulationRuleBase(BaseModel):
    rule_name: str
    rule_priority: int = 100
    rule_condition: RuleCondition
    rule_action: RuleAction
    rule_category: FormulationRuleCategory
    is_active: bool = True
    source_id: Optional[UUID] = None
    evidence_status: IntermixEvidenceStatus
    test_coverage: bool = False


class FormulationRuleCreate(FormulationRuleBase):
    brand_ids: list[UUID] = Field(
        default_factory=list,
        description="Empty = universal rule across all brands",
    )
    line_ids: list[UUID] = Field(
        default_factory=list,
        description="When set, restricts to listed product lines",
    )


class FormulationRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    rule_priority: Optional[int] = None
    rule_condition: Optional[RuleCondition] = None
    rule_action: Optional[RuleAction] = None
    rule_category: Optional[FormulationRuleCategory] = None
    is_active: Optional[bool] = None
    source_id: Optional[UUID] = None
    evidence_status: Optional[IntermixEvidenceStatus] = None
    test_coverage: Optional[bool] = None
    brand_ids: Optional[list[UUID]] = None
    line_ids: Optional[list[UUID]] = None


class FormulationRuleBrandResponse(BaseModel):
    rule_id: UUID
    brand_id: UUID

    model_config = ConfigDict(from_attributes=True)


class FormulationRuleLineResponse(BaseModel):
    rule_id: UUID
    line_id: UUID

    model_config = ConfigDict(from_attributes=True)


class FormulationRuleResponse(FormulationRuleBase):
    rule_id: UUID
    created_at: datetime
    updated_at: datetime
    brand_links: list[FormulationRuleBrandResponse] = Field(default_factory=list)
    line_links: list[FormulationRuleLineResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# E. Operational PRD domain tables
# ---------------------------------------------------------------------------


class ConsultationBase(BaseModel):
    client_id: Optional[UUID] = None
    stylist_id: UUID
    salon_id: Optional[UUID] = None
    status: ConsultationStatus = ConsultationStatus.DRAFT
    ai_parsed_raw: Optional[str] = None
    parser_confidence: Optional[Decimal] = Field(None, ge=0, le=1)


class ConsultationCreate(ConsultationBase):
    pass


class ConsultationUpdate(BaseModel):
    client_id: Optional[UUID] = None
    stylist_id: Optional[UUID] = None
    salon_id: Optional[UUID] = None
    completed_at: Optional[datetime] = None
    status: Optional[ConsultationStatus] = None
    ai_parsed_raw: Optional[str] = None
    parser_confidence: Optional[Decimal] = Field(None, ge=0, le=1)


class ConsultationResponse(ConsultationBase):
    consultation_id: UUID
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("parser_confidence")
    @classmethod
    def validate_parser_confidence(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            return _validate_unit_interval(v)
        return v


class HairProfileBase(BaseModel):
    natural_level: int
    existing_level: Optional[int] = None
    existing_artificial_color: Optional[str] = None
    porosity: int
    elasticity: int
    gray_percentage: int
    texture: HairTexture
    scalp_condition: ScalpCondition
    chemical_history: list[Any] = Field(default_factory=list)
    desired_result: str
    desired_tone: Optional[str] = None
    desired_level: Optional[int] = None
    photo_urls: Optional[list[str]] = None
    intake_source: IntakeSource
    data_confidence: Decimal = Field(..., ge=0, le=1)

    @field_validator("natural_level", "desired_level")
    @classmethod
    def validate_levels(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            return _validate_level(v)
        return v

    @field_validator("existing_level")
    @classmethod
    def validate_existing_level(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            return _validate_level(v)
        return v

    @field_validator("porosity", "elasticity")
    @classmethod
    def validate_porosity_elasticity(cls, v: int) -> int:
        return _validate_porosity_elasticity(v)

    @field_validator("gray_percentage")
    @classmethod
    def validate_gray(cls, v: int) -> int:
        return _validate_gray_percentage(v)

    @field_validator("data_confidence")
    @classmethod
    def validate_data_confidence(cls, v: Decimal) -> Decimal:
        return _validate_unit_interval(v)


class HairProfileCreate(HairProfileBase):
    consultation_id: UUID


class HairProfileUpdate(BaseModel):
    natural_level: Optional[int] = None
    existing_level: Optional[int] = None
    existing_artificial_color: Optional[str] = None
    porosity: Optional[int] = None
    elasticity: Optional[int] = None
    gray_percentage: Optional[int] = None
    texture: Optional[HairTexture] = None
    scalp_condition: Optional[ScalpCondition] = None
    chemical_history: Optional[list[Any]] = None
    desired_result: Optional[str] = None
    desired_tone: Optional[str] = None
    desired_level: Optional[int] = None
    photo_urls: Optional[list[str]] = None
    intake_source: Optional[IntakeSource] = None
    data_confidence: Optional[Decimal] = Field(None, ge=0, le=1)


class HairProfileResponse(HairProfileBase):
    profile_id: UUID
    consultation_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FormulaBase(BaseModel):
    line_id: UUID
    recommendation_type: RecommendationType
    status: FormulaStatus = FormulaStatus.DRAFT
    risk_score: Decimal = Field(..., ge=0, le=1)
    total_processing_time: int
    ai_explanation: Optional[str] = None
    stylist_notes: Optional[str] = None
    is_favorite: bool = False

    @field_validator("risk_score")
    @classmethod
    def validate_risk_score(cls, v: Decimal) -> Decimal:
        return _validate_unit_interval(v)


class FormulaCreate(FormulaBase):
    consultation_id: UUID


class FormulaUpdate(BaseModel):
    line_id: Optional[UUID] = None
    recommendation_type: Optional[RecommendationType] = None
    status: Optional[FormulaStatus] = None
    risk_score: Optional[Decimal] = Field(None, ge=0, le=1)
    total_processing_time: Optional[int] = None
    ai_explanation: Optional[str] = None
    stylist_notes: Optional[str] = None
    used_at: Optional[datetime] = None
    is_favorite: Optional[bool] = None


class FormulaResponse(FormulaBase):
    formula_id: UUID
    consultation_id: UUID
    created_at: datetime
    used_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FormulaStepBase(BaseModel):
    step_order: int
    zone: FormulaZone
    shade_id: Optional[UUID] = None
    developer_id: Optional[UUID] = None
    mixing_ratio: Optional[str] = None
    quantity_grams: Optional[int] = None
    processing_time_minutes: Optional[int] = None
    special_instructions: Optional[str] = None
    is_optional: bool = False


class FormulaStepCreate(FormulaStepBase):
    formula_id: UUID


class FormulaStepUpdate(BaseModel):
    step_order: Optional[int] = None
    zone: Optional[FormulaZone] = None
    shade_id: Optional[UUID] = None
    developer_id: Optional[UUID] = None
    mixing_ratio: Optional[str] = None
    quantity_grams: Optional[int] = None
    processing_time_minutes: Optional[int] = None
    special_instructions: Optional[str] = None
    is_optional: Optional[bool] = None


class FormulaStepResponse(FormulaStepBase):
    step_id: UUID
    formula_id: UUID

    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentBase(BaseModel):
    risk_type: RiskType
    probability: Decimal = Field(..., ge=0, le=1)
    severity: RiskSeverity
    contributing_factors: list[Any] = Field(default_factory=list)
    mitigation: str
    requires_waiver: bool = False
    waiver_text: Optional[str] = None

    @field_validator("probability")
    @classmethod
    def validate_probability(cls, v: Decimal) -> Decimal:
        return _validate_unit_interval(v)


class RiskAssessmentCreate(RiskAssessmentBase):
    formula_id: UUID


class RiskAssessmentUpdate(BaseModel):
    risk_type: Optional[RiskType] = None
    probability: Optional[Decimal] = Field(None, ge=0, le=1)
    severity: Optional[RiskSeverity] = None
    contributing_factors: Optional[list[Any]] = None
    mitigation: Optional[str] = None
    requires_waiver: Optional[bool] = None
    waiver_text: Optional[str] = None


class RiskAssessmentResponse(RiskAssessmentBase):
    assessment_id: UUID
    formula_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FormulaOutcomeBase(BaseModel):
    actual_result: str
    client_satisfaction: int = Field(..., ge=1, le=10)
    color_accuracy: Optional[int] = Field(None, ge=1, le=10)
    condition_after: Optional[int] = Field(None, ge=1, le=10)
    photos: Optional[list[str]] = None
    corrective_service_needed: bool = False
    corrective_service_description: Optional[str] = None
    reported_by: Optional[UUID] = None


class FormulaOutcomeCreate(FormulaOutcomeBase):
    formula_id: UUID


class FormulaOutcomeUpdate(BaseModel):
    actual_result: Optional[str] = None
    client_satisfaction: Optional[int] = Field(None, ge=1, le=10)
    color_accuracy: Optional[int] = Field(None, ge=1, le=10)
    condition_after: Optional[int] = Field(None, ge=1, le=10)
    photos: Optional[list[str]] = None
    corrective_service_needed: Optional[bool] = None
    corrective_service_description: Optional[str] = None
    reported_by: Optional[UUID] = None


class FormulaOutcomeResponse(FormulaOutcomeBase):
    outcome_id: UUID
    formula_id: UUID
    reported_at: datetime

    model_config = ConfigDict(from_attributes=True)
