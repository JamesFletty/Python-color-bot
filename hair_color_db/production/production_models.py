"""SQLAlchemy 2.0 ORM models for the operational / production schema layer.

Assumes research-layer tables (brand, shade, line_technical_rule, etc.) already exist.
Only operational additions and the additive line_technical_rule columns are defined here,
with minimal research stubs for relationship wiring.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for operational models."""


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist native PostgreSQL enums by their (lowercase) value, not member name.

    SQLAlchemy's ``Enum`` defaults to storing the Python member *name* (e.g.
    ``SAFETY``), but the PostgreSQL enum types are created with lowercase value
    labels (e.g. ``safety``). Passing this as ``values_callable`` keeps bind and
    result handling aligned with the database labels.
    """
    return [member.value for member in enum_cls]


# ---------------------------------------------------------------------------
# Minimal research-layer stubs (PKs only — full models live in research ingest)
# ---------------------------------------------------------------------------


class Brand(Base):
    __tablename__ = "brand"

    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    brand_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    parent_company: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    official_brand_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    formulation_rule_brands: Mapped[list["FormulationRuleBrand"]] = relationship(
        back_populates="brand"
    )
    product_lines: Mapped[list["ProductLine"]] = relationship(back_populates="brand")


class ProductLine(Base):
    __tablename__ = "product_line"

    line_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brand.brand_id"), nullable=False
    )
    product_line_name: Mapped[str] = mapped_column(String, nullable=False)
    line_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    code_grammar: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    apparent_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    official_line_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    brand: Mapped["Brand"] = relationship(back_populates="product_lines")
    formulation_rule_lines: Mapped[list["FormulationRuleLine"]] = relationship(
        back_populates="product_line"
    )
    formulas: Mapped[list["Formula"]] = relationship(back_populates="product_line")
    regions: Mapped[list["ProductLineRegion"]] = relationship(back_populates="product_line")

    __table_args__ = (
        UniqueConstraint("brand_id", "product_line_name", name="uq_product_line_brand_name"),
    )


class ProductLineRegion(Base):
    __tablename__ = "product_line_region"

    line_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_line.line_id"), nullable=False
    )
    region_or_market: Mapped[str] = mapped_column(String, nullable=False)
    canonical_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    discontinued_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    product_line: Mapped["ProductLine"] = relationship(back_populates="regions")
    intermixing_rules: Mapped[list["ShadeIntermixingRule"]] = relationship(
        back_populates="line_region"
    )
    sub_ranges: Mapped[list["SubRange"]] = relationship(back_populates="line_region")


class SubRange(Base):
    __tablename__ = "sub_range"

    sub_range_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    line_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_line_region.line_region_id"), nullable=False
    )
    sub_range_name: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    line_region: Mapped["ProductLineRegion"] = relationship(back_populates="sub_ranges")

    __table_args__ = (
        UniqueConstraint("line_region_id", "sub_range_name", name="uq_sub_range_line_name"),
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_run"

    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    batch_label: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tooling_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SourceDocument(Base):
    __tablename__ = "source_document"

    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    source_title: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    publisher_domain: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    publication_or_revision_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    access_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_priority_tier: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    region_or_market: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class ShadeRaw(Base):
    __tablename__ = "shade_raw"

    shade_raw_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    line_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_line_region.line_region_id"), nullable=False
    )
    sub_range_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sub_range.sub_range_id"), nullable=True
    )
    shade_code_raw: Mapped[str] = mapped_column(String, nullable=False)
    shade_name_raw: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    level_raw: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    tone_codes_raw: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    tone_descriptions_raw: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    gray_coverage_claim_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lift_capability_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mixing_ratio_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    developer_recommendations_raw: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    processing_time_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    special_usage_notes_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    official_swatch_image_exists: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_document.source_id"), nullable=False
    )
    source_confidence: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evidence_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    assumptions: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    data_gaps: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_run.ingestion_run_id"), nullable=False
    )


class Shade(Base):
    __tablename__ = "shade"

    shade_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    shade_raw_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shade_raw.shade_raw_id"), nullable=False
    )
    line_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_line_region.line_region_id"), nullable=False
    )
    sub_range_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sub_range.sub_range_id"), nullable=True
    )
    shade_code: Mapped[str] = mapped_column(String, nullable=False)
    shade_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    level: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    color_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gray_coverage_claim: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lift_levels: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mixing_ratio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mixing_ratio_inherited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    processing_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_time_inherited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint(
            "line_region_id", "sub_range_id", "shade_code", name="uq_shade_region_subrange_code"
        ),
        Index("idx_shade_lookup", "line_region_id", "sub_range_id", "shade_code"),
    )


class Developer(Base):
    __tablename__ = "developer"

    developer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)


class NormalizedTone(Base):
    __tablename__ = "normalized_tone"

    normalized_tone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    tone_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class ToneCodeReference(Base):
    __tablename__ = "tone_code_reference"

    tone_code_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    line_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_line_region.line_region_id"), nullable=False
    )
    manufacturer_tone_code: Mapped[str] = mapped_column(String, nullable=False)
    manufacturer_term: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    manufacturer_definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes_on_ambiguity: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_document.source_id"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "line_region_id",
            "manufacturer_tone_code",
            name="uq_tone_code_region_code",
        ),
    )


class ToneNormalization(Base):
    __tablename__ = "tone_normalization"

    tone_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tone_code_reference.tone_code_id"), primary_key=True
    )
    normalized_tone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("normalized_tone.normalized_tone_id"), primary_key=True
    )
    mapping_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mapping_confidence: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ambiguity_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ShadeToneCode(Base):
    __tablename__ = "shade_tone_code"

    shade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shade.shade_id"), primary_key=True
    )
    tone_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tone_code_reference.tone_code_id"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class LineTechnicalRule(Base):
    """Research table with additive typed columns for queryable rule facets."""

    __tablename__ = "line_technical_rule"

    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    line_region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_line_region.line_region_id"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(String, nullable=False)
    rule_value: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    applies_to_sub_range_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sub_range.sub_range_id"), nullable=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_document.source_id"), nullable=False
    )
    source_confidence: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evidence_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    developer_volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_lift_levels: Mapped[Optional[Decimal]] = mapped_column(Numeric(2, 1), nullable=True)
    gray_coverage_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mixing_ratio_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mixing_ratio_den: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_time_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    applicable_hair_type: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )
    porosity_adjustment: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "rule_value IS NOT NULL OR developer_volume IS NOT NULL "
            "OR max_lift_levels IS NOT NULL OR gray_coverage_pct IS NOT NULL "
            "OR mixing_ratio_num IS NOT NULL OR mixing_ratio_den IS NOT NULL "
            "OR processing_time_min IS NOT NULL OR applicable_hair_type IS NOT NULL "
            "OR porosity_adjustment IS NOT NULL",
            name="chk_ltr_has_payload",
        ),
        CheckConstraint(
            "gray_coverage_pct IS NULL OR gray_coverage_pct BETWEEN 0 AND 100",
            name="chk_ltr_gray_coverage_pct",
        ),
        CheckConstraint(
            "developer_volume IS NULL OR (developer_volume > 0 AND developer_volume <= 100)",
            name="chk_ltr_developer_volume",
        ),
        CheckConstraint(
            "processing_time_min IS NULL OR processing_time_min > 0",
            name="chk_ltr_processing_time_min",
        ),
        CheckConstraint(
            "max_lift_levels IS NULL OR max_lift_levels >= 0",
            name="chk_ltr_max_lift_levels",
        ),
        CheckConstraint(
            "(mixing_ratio_num IS NULL AND mixing_ratio_den IS NULL) OR "
            "(mixing_ratio_num IS NOT NULL AND mixing_ratio_den IS NOT NULL "
            "AND mixing_ratio_num > 0 AND mixing_ratio_den > 0)",
            name="chk_ltr_mixing_ratio_pair",
        ),
    )


# ---------------------------------------------------------------------------
# Operational enums
# ---------------------------------------------------------------------------


class ColorScienceConfidence(str, enum.Enum):
    ESTABLISHED = "established"
    DEBATED = "debated"
    INFERRED = "inferred"


class IntermixRestrictionType(str, enum.Enum):
    NOT_MIXABLE = "not_mixable"
    CAUTION = "caution"
    RATIO_REQUIRED = "ratio_required"
    DEVELOPER_OVERRIDE = "developer_override"


class IntermixEvidenceStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    MANUFACTURER_STATED = "manufacturer_stated"
    EDUCATOR_REPORTED = "educator_reported"
    INFERRED = "inferred"


class IntermixRuleScope(str, enum.Enum):
    SHADE_PAIR = "shade_pair"
    SUB_RANGE_INTERNAL_ONLY = "sub_range_internal_only"
    SUB_RANGE_ISOLATED_FROM_LINE = "sub_range_isolated_from_line"
    CROSS_SUB_RANGE = "cross_sub_range"


class FormulationRuleCategory(str, enum.Enum):
    LIFT = "lift"
    TONE = "tone"
    NEUTRALIZATION = "neutralization"
    GRAY_COVERAGE = "gray_coverage"
    POROSITY = "porosity"
    CORRECTION = "correction"
    DEVELOPER = "developer"
    DEPOSIT = "deposit"
    PROCESSING = "processing"
    SAFETY = "safety"
    COLOR_SCIENCE = "color_science"
    PRODUCT_TYPE = "product_type"
    APPLICATION = "application"
    INTERMIXING = "intermixing"


class ConsultationStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class HairTexture(str, enum.Enum):
    FINE = "fine"
    MEDIUM = "medium"
    COARSE = "coarse"


class ScalpCondition(str, enum.Enum):
    NORMAL = "normal"
    SENSITIVE = "sensitive"
    IRRITATED = "irritated"
    COMPROMISED = "compromised"


class IntakeSource(str, enum.Enum):
    AI_PARSED = "ai_parsed"
    MANUAL_ENTRY = "manual_entry"
    HYBRID = "hybrid"


class RecommendationType(str, enum.Enum):
    SAFEST = "safest"
    FASTEST = "fastest"
    HIGHEST_FIDELITY = "highest_fidelity"


class FormulaStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    USED = "used"
    DISCARDED = "discarded"
    EXPIRED = "expired"


class FormulaZone(str, enum.Enum):
    ROOT = "root"
    MID = "mid"
    END = "end"
    ALL = "all"
    FACE_FRAME = "face_frame"
    CROWN = "crown"


class RiskType(str, enum.Enum):
    BREAKAGE = "breakage"
    BANDING = "banding"
    OVERLAP = "overlap"
    GRAY_COVERAGE = "gray_coverage"
    POROSITY_MISMATCH = "porosity_mismatch"
    UNREALISTIC_EXPECTATION = "unrealistic_expectation"
    ALLERGIC_REACTION = "allergic_reaction"
    SCALP_IRRITATION = "scalp_irritation"


class RiskSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# A. universal_color_science
# ---------------------------------------------------------------------------


class UniversalColorScience(Base):
    __tablename__ = "universal_color_science"

    level: Mapped[int] = mapped_column(Integer, primary_key=True)
    underlying_pigment: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    neutralizing_tone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    neutralizing_tone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("normalized_tone.normalized_tone_id", ondelete="SET NULL"),
        nullable=True,
    )
    exposure_stage: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_label: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_document.source_id", ondelete="SET NULL"),
        nullable=True,
    )
    confidence: Mapped[ColorScienceConfidence] = mapped_column(
        Enum(ColorScienceConfidence, name="color_science_confidence", create_type=False, values_callable=_enum_values),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    neutralizing_tone_ref: Mapped[Optional["NormalizedTone"]] = relationship()

    __table_args__ = (
        CheckConstraint("level BETWEEN 1 AND 12", name="chk_ucs_level"),
    )


# ---------------------------------------------------------------------------
# C. shade_intermixing_rule
# ---------------------------------------------------------------------------


class ShadeIntermixingRule(Base):
    __tablename__ = "shade_intermixing_rule"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    line_region_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_line_region.line_region_id", ondelete="RESTRICT"),
        nullable=True,
    )
    applies_to_sub_range_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_range.sub_range_id", ondelete="RESTRICT"),
        nullable=True,
    )
    compatible_sub_range_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_range.sub_range_id", ondelete="RESTRICT"),
        nullable=True,
    )
    shade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shade.shade_id", ondelete="RESTRICT"),
        nullable=True,
    )
    compatible_shade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shade.shade_id", ondelete="RESTRICT"),
        nullable=True,
    )
    rule_scope: Mapped[IntermixRuleScope] = mapped_column(
        Enum(IntermixRuleScope, name="intermix_rule_scope", create_type=False, values_callable=_enum_values),
        nullable=False,
    )
    restriction_type: Mapped[IntermixRestrictionType] = mapped_column(
        Enum(IntermixRestrictionType, name="intermix_restriction_type", create_type=False, values_callable=_enum_values),
        nullable=False,
    )
    restriction_note: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_document.source_id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_status: Mapped[IntermixEvidenceStatus] = mapped_column(
        Enum(IntermixEvidenceStatus, name="intermix_evidence_status", create_type=False, values_callable=_enum_values),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    line_region: Mapped[Optional["ProductLineRegion"]] = relationship(
        back_populates="intermixing_rules"
    )
    source: Mapped["SourceDocument"] = relationship()

    __table_args__ = (
        Index(
            "idx_shade_intermixing_applies",
            "line_region_id",
            "applies_to_sub_range_id",
        ),
    )


# ---------------------------------------------------------------------------
# D. formulation_rule + join tables
# ---------------------------------------------------------------------------


class FormulationRule(Base):
    __tablename__ = "formulation_rule"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    rule_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    rule_condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rule_action: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rule_category: Mapped[FormulationRuleCategory] = mapped_column(
        Enum(FormulationRuleCategory, name="formulation_rule_category", create_type=False, values_callable=_enum_values),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_document.source_id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_status: Mapped[IntermixEvidenceStatus] = mapped_column(
        Enum(IntermixEvidenceStatus, name="intermix_evidence_status", create_type=False, values_callable=_enum_values),
        nullable=False,
    )
    test_coverage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    package_rule_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)
    scope_level: Mapped[str] = mapped_column(String, nullable=False, default="universal")
    canonical_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_dormant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    brand_links: Mapped[list["FormulationRuleBrand"]] = relationship(
        back_populates="formulation_rule", cascade="all, delete-orphan"
    )
    line_links: Mapped[list["FormulationRuleLine"]] = relationship(
        back_populates="formulation_rule", cascade="all, delete-orphan"
    )
    source: Mapped[Optional["SourceDocument"]] = relationship()

    __table_args__ = (
        Index(
            "idx_formulation_rule_active",
            "is_active",
            "rule_category",
            "rule_priority",
        ),
        Index(
            "idx_formulation_rule_condition_gin",
            "rule_condition",
            postgresql_using="gin",
        ),
    )


class FormulationRuleBrand(Base):
    __tablename__ = "formulation_rule_brand"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("formulation_rule.rule_id", ondelete="CASCADE"),
        primary_key=True,
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brand.brand_id", ondelete="CASCADE"),
        primary_key=True,
    )

    formulation_rule: Mapped["FormulationRule"] = relationship(
        back_populates="brand_links"
    )
    brand: Mapped["Brand"] = relationship(back_populates="formulation_rule_brands")


class FormulationRuleLine(Base):
    __tablename__ = "formulation_rule_line"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("formulation_rule.rule_id", ondelete="CASCADE"),
        primary_key=True,
    )
    line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_line.line_id", ondelete="CASCADE"),
        primary_key=True,
    )

    formulation_rule: Mapped["FormulationRule"] = relationship(
        back_populates="line_links"
    )
    product_line: Mapped["ProductLine"] = relationship(
        back_populates="formulation_rule_lines"
    )


class ServiceWorkflow(Base):
    __tablename__ = "service_workflow"

    workflow_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    service_intent: Mapped[str] = mapped_column(String, nullable=False)
    steps: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    default_zones: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    applicable_line_categories: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)


class ValidationCase(Base):
    __tablename__ = "validation_case"

    case_id: Mapped[str] = mapped_column(String, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expected: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class FormulationRuleEvidence(Base):
    __tablename__ = "formulation_rule_evidence"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("formulation_rule.rule_id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_document.source_id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_status: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# E. Operational PRD domain tables
# ---------------------------------------------------------------------------


class Consultation(Base):
    __tablename__ = "consultation"

    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    stylist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    salon_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[ConsultationStatus] = mapped_column(
        Enum(ConsultationStatus, name="consultation_status", create_type=False, values_callable=_enum_values),
        nullable=False,
        default=ConsultationStatus.DRAFT,
    )
    ai_parsed_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parser_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), nullable=True)

    hair_profiles: Mapped[list["HairProfile"]] = relationship(
        back_populates="consultation", cascade="all, delete-orphan"
    )
    formulas: Mapped[list["Formula"]] = relationship(
        back_populates="consultation"
    )

    __table_args__ = (
        CheckConstraint(
            "parser_confidence IS NULL OR parser_confidence BETWEEN 0 AND 1",
            name="chk_consultation_parser_confidence",
        ),
    )


class HairProfile(Base):
    __tablename__ = "hair_profile"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultation.consultation_id", ondelete="CASCADE"),
        nullable=False,
    )
    natural_level: Mapped[int] = mapped_column(Integer, nullable=False)
    existing_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    existing_artificial_color: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    porosity: Mapped[int] = mapped_column(Integer, nullable=False)
    elasticity: Mapped[int] = mapped_column(Integer, nullable=False)
    gray_percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    texture: Mapped[HairTexture] = mapped_column(
        Enum(HairTexture, name="hair_texture", create_type=False, values_callable=_enum_values), nullable=False
    )
    scalp_condition: Mapped[ScalpCondition] = mapped_column(
        Enum(ScalpCondition, name="scalp_condition", create_type=False, values_callable=_enum_values), nullable=False
    )
    chemical_history: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    desired_result: Mapped[str] = mapped_column(Text, nullable=False)
    desired_tone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    desired_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    photo_urls: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    intake_source: Mapped[IntakeSource] = mapped_column(
        Enum(IntakeSource, name="intake_source", create_type=False, values_callable=_enum_values), nullable=False
    )
    data_confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    consultation: Mapped["Consultation"] = relationship(back_populates="hair_profiles")

    __table_args__ = (
        CheckConstraint("natural_level BETWEEN 1 AND 12", name="chk_hp_natural_level"),
        CheckConstraint(
            "existing_level IS NULL OR existing_level BETWEEN 1 AND 12",
            name="chk_hp_existing_level",
        ),
        CheckConstraint(
            "desired_level IS NULL OR desired_level BETWEEN 1 AND 12",
            name="chk_hp_desired_level",
        ),
        CheckConstraint("porosity BETWEEN 1 AND 10", name="chk_hp_porosity"),
        CheckConstraint("elasticity BETWEEN 1 AND 10", name="chk_hp_elasticity"),
        CheckConstraint("gray_percentage BETWEEN 0 AND 100", name="chk_hp_gray_percentage"),
        CheckConstraint(
            "data_confidence BETWEEN 0 AND 1", name="chk_hp_data_confidence"
        ),
        Index(
            "idx_hair_profile_chemical_history_gin",
            "chemical_history",
            postgresql_using="gin",
        ),
    )


class Formula(Base):
    __tablename__ = "formula"

    formula_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultation.consultation_id", ondelete="RESTRICT"),
        nullable=False,
    )
    line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_line.line_id", ondelete="RESTRICT"),
        nullable=False,
    )
    recommendation_type: Mapped[RecommendationType] = mapped_column(
        Enum(RecommendationType, name="recommendation_type", create_type=False, values_callable=_enum_values),
        nullable=False,
    )
    status: Mapped[FormulaStatus] = mapped_column(
        Enum(FormulaStatus, name="formula_status", create_type=False, values_callable=_enum_values),
        nullable=False,
        default=FormulaStatus.DRAFT,
    )
    risk_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    total_processing_time: Mapped[int] = mapped_column(Integer, nullable=False)
    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stylist_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    consultation: Mapped["Consultation"] = relationship(back_populates="formulas")
    product_line: Mapped["ProductLine"] = relationship(back_populates="formulas")
    steps: Mapped[list["FormulaStep"]] = relationship(
        back_populates="formula", cascade="all, delete-orphan"
    )
    risk_assessments: Mapped[list["RiskAssessment"]] = relationship(
        back_populates="formula", cascade="all, delete-orphan"
    )
    outcomes: Mapped[list["FormulaOutcome"]] = relationship(back_populates="formula")

    __table_args__ = (
        CheckConstraint("risk_score BETWEEN 0 AND 1", name="chk_formula_risk_score"),
        Index("idx_formula_consultation", "consultation_id", "status"),
    )


class FormulaStep(Base):
    __tablename__ = "formula_step"

    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    formula_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("formula.formula_id", ondelete="CASCADE"),
        nullable=False,
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    zone: Mapped[FormulaZone] = mapped_column(
        Enum(FormulaZone, name="formula_zone", create_type=False, values_callable=_enum_values), nullable=False
    )
    shade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shade.shade_id", ondelete="SET NULL"), nullable=True
    )
    developer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("developer.developer_id", ondelete="SET NULL"),
        nullable=True,
    )
    mixing_ratio: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    quantity_grams: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    special_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_optional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    formula: Mapped["Formula"] = relationship(back_populates="steps")
    shade: Mapped[Optional["Shade"]] = relationship()
    developer: Mapped[Optional["Developer"]] = relationship()

    __table_args__ = (
        UniqueConstraint("formula_id", "step_order", name="uq_formula_step_order"),
    )


class RiskAssessment(Base):
    __tablename__ = "risk_assessment"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    formula_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("formula.formula_id", ondelete="CASCADE"),
        nullable=False,
    )
    risk_type: Mapped[RiskType] = mapped_column(
        Enum(RiskType, name="risk_type", create_type=False, values_callable=_enum_values), nullable=False
    )
    probability: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    severity: Mapped[RiskSeverity] = mapped_column(
        Enum(RiskSeverity, name="risk_severity", create_type=False, values_callable=_enum_values), nullable=False
    )
    contributing_factors: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    mitigation: Mapped[str] = mapped_column(Text, nullable=False)
    requires_waiver: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    waiver_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    formula: Mapped["Formula"] = relationship(back_populates="risk_assessments")

    __table_args__ = (
        CheckConstraint("probability BETWEEN 0 AND 1", name="chk_risk_probability"),
        Index("idx_risk_assessment_formula", "formula_id", "risk_type"),
    )


class FormulaOutcome(Base):
    __tablename__ = "formula_outcome"

    outcome_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    formula_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("formula.formula_id", ondelete="RESTRICT"),
        nullable=False,
    )
    actual_result: Mapped[str] = mapped_column(Text, nullable=False)
    client_satisfaction: Mapped[int] = mapped_column(Integer, nullable=False)
    color_accuracy: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    condition_after: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    photos: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    corrective_service_needed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    corrective_service_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    reported_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    formula: Mapped["Formula"] = relationship(back_populates="outcomes")

    __table_args__ = (
        CheckConstraint(
            "client_satisfaction BETWEEN 1 AND 10", name="chk_outcome_satisfaction"
        ),
        CheckConstraint(
            "color_accuracy IS NULL OR color_accuracy BETWEEN 1 AND 10",
            name="chk_outcome_color_accuracy",
        ),
        CheckConstraint(
            "condition_after IS NULL OR condition_after BETWEEN 1 AND 10",
            name="chk_outcome_condition_after",
        ),
    )
