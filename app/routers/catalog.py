"""Catalog routes — brands and shades."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.catalog import BrandSummary, ShadeSummary
from app.services.catalog_service import get_line, list_brands, list_shades_for_line

router = APIRouter(tags=["catalog"])


@router.get("/brands", response_model=list[BrandSummary])
def get_brands(db: Session = Depends(get_db)) -> list[BrandSummary]:
    return list_brands(db)


@router.get("/lines/{line_id}/shades", response_model=list[ShadeSummary])
def get_line_shades(
    line_id: int,
    q: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[ShadeSummary]:
    if get_line(db, line_id) is None:
        raise HTTPException(status_code=404, detail=f"Line {line_id} not found")
    return list_shades_for_line(db, line_id, query=q, limit=limit)
