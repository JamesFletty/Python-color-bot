"""Deterministic formula route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.formula import FormulaRequest, FormulaResponse
from app.services.formula_engine import ShadeNotFoundError, build_formula

router = APIRouter(tags=["formula"])


@router.post("/formula", response_model=FormulaResponse)
def post_formula(
    body: FormulaRequest,
    db: Session = Depends(get_db),
) -> FormulaResponse:
    try:
        return build_formula(body, db)
    except ShadeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Formula engine error: {exc}") from exc
