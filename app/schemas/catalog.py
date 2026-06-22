"""Catalog DTOs for v2 API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LineSummary(BaseModel):
    line_id: int
    line_name: str
    canonical_key: str
    color_type: Optional[str] = None
    region_or_market: Optional[str] = None


class BrandSummary(BaseModel):
    brand_id: int
    brand_name: str
    lines: list[LineSummary] = Field(default_factory=list)


class ShadeSummary(BaseModel):
    shade_id: int
    shade_code: str
    shade_name: Optional[str] = None
    level: Optional[float] = None
    normalized_tones: list[str] = Field(default_factory=list)
    sub_range: Optional[str] = None
    color_type: Optional[str] = None
