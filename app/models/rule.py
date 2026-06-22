"""Formulation rules and cross-line mapping models (v2)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from app.models.shade import ProductLine


class FormulationRule(Base):
    __tablename__ = "formulation_rules"

    rule_id: Mapped[int] = mapped_column(primary_key=True)
    package_rule_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    line_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_lines.line_id"), nullable=True)
    scope_level: Mapped[str] = mapped_column(Text, nullable=False, default="universal")
    sub_range: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rule_name: Mapped[str] = mapped_column(Text, nullable=False)
    rule_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    rule_category: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rule_condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rule_action: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_dormant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    warnings: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)

    line: Mapped[Optional["ProductLine"]] = relationship("ProductLine")


class CrossLineMapping(Base):
    __tablename__ = "cross_line_mappings"

    mapping_id: Mapped[int] = mapped_column(primary_key=True)
    conversion_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_line_id: Mapped[int] = mapped_column(ForeignKey("product_lines.line_id"), nullable=False)
    source_shade_code: Mapped[str] = mapped_column(Text, nullable=False)
    target_line_id: Mapped[int] = mapped_column(ForeignKey("product_lines.line_id"), nullable=False)
    target_shade_code: Mapped[str] = mapped_column(Text, nullable=False)
    strategy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(Text, default="exact", nullable=False)
    component_role: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_document: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "source_line_id",
            "source_shade_code",
            "target_line_id",
            "component_role",
            name="uq_cross_line_source_target_role",
        ),
    )


class Consultation(Base):
    """Stub table — no API surface in v2 Phase 2."""

    __tablename__ = "consultations"

    consultation_id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    shade_id: Mapped[Optional[int]] = mapped_column(ForeignKey("shades.shade_id"), nullable=True)
    formula_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
