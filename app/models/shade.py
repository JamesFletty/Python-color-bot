"""Shade catalog ORM models (v2 simplified schema)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Brand(Base):
    __tablename__ = "brands"

    brand_id: Mapped[int] = mapped_column(primary_key=True)
    brand_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    product_lines: Mapped[list["ProductLine"]] = relationship(back_populates="brand")


class ProductLine(Base):
    __tablename__ = "product_lines"

    line_id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.brand_id"), nullable=False)
    line_name: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    color_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mixing_ratio_default: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    region_or_market: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    brand: Mapped["Brand"] = relationship(back_populates="product_lines")
    shades: Mapped[list["Shade"]] = relationship(back_populates="line")

    __table_args__ = (
        UniqueConstraint("brand_id", "line_name", name="uq_product_lines_brand_line_name"),
    )


class Shade(Base):
    __tablename__ = "shades"

    shade_id: Mapped[int] = mapped_column(primary_key=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("product_lines.line_id"), nullable=False)
    shade_code: Mapped[str] = mapped_column(Text, nullable=False)
    shade_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    level: Mapped[Optional[float]] = mapped_column(Numeric(3, 1), nullable=True)
    color_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sub_range: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mixing_ratio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discontinued: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gray_coverage_claim: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    line: Mapped["ProductLine"] = relationship(back_populates="shades")
    tones: Mapped[list["ShadeTone"]] = relationship(
        back_populates="shade", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("line_id", "shade_code", "sub_range", name="uq_shades_line_code_subrange"),
    )


class ShadeTone(Base):
    __tablename__ = "shade_tones"

    shade_id: Mapped[int] = mapped_column(ForeignKey("shades.shade_id"), primary_key=True)
    tone_name: Mapped[str] = mapped_column(Text, primary_key=True)
    position: Mapped[int] = mapped_column(default=0, nullable=False)

    shade: Mapped["Shade"] = relationship(back_populates="tones")
