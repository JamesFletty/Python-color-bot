"""Persist engine output to PostgreSQL operational tables."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from .engine_models import EngineInput, EngineOutput, PersistencePayload
from .production_models import (
    Consultation,
    ConsultationStatus,
    Formula,
    FormulaStatus,
    FormulaStep,
    FormulaZone,
    RecommendationType,
    RiskAssessment,
    RiskSeverity,
    RiskType,
)

# Default stylist for bootstrap / CLI runs without an auth layer.
SYSTEM_STYLIST_ID = uuid.UUID("00000000-0000-4000-8000-000000009001")


def ensure_consultation(
    session: Session,
    consultation_id: uuid.UUID,
    *,
    stylist_id: uuid.UUID = SYSTEM_STYLIST_ID,
    client_id: uuid.UUID | None = None,
    salon_id: uuid.UUID | None = None,
) -> Consultation:
    """Create a draft consultation row when missing (required for formula FK)."""
    existing = session.get(Consultation, consultation_id)
    if existing:
        if client_id is not None:
            existing.client_id = client_id
        if salon_id is not None:
            existing.salon_id = salon_id
        if stylist_id != SYSTEM_STYLIST_ID:
            existing.stylist_id = stylist_id
        return existing
    consultation = Consultation(
        consultation_id=consultation_id,
        client_id=client_id,
        stylist_id=stylist_id,
        salon_id=salon_id,
        status=ConsultationStatus.DRAFT,
    )
    session.add(consultation)
    session.flush()
    return consultation


def persist_formula_payload(
    session: Session,
    payload: PersistencePayload,
    *,
    consultation_id: uuid.UUID,
    stylist_id: uuid.UUID = SYSTEM_STYLIST_ID,
    client_id: uuid.UUID | None = None,
    salon_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Write formula, steps, and risk assessments from a persistence payload."""
    ensure_consultation(
        session,
        consultation_id,
        stylist_id=stylist_id,
        client_id=client_id,
        salon_id=salon_id,
    )

    formula_data = dict(payload.formula)
    formula_data["consultation_id"] = consultation_id
    formula_id = formula_data["formula_id"]

    formula = Formula(
        formula_id=formula_id,
        consultation_id=consultation_id,
        line_id=formula_data["line_id"],
        recommendation_type=RecommendationType(formula_data["recommendation_type"]),
        status=FormulaStatus(formula_data["status"]),
        risk_score=Decimal(str(formula_data["risk_score"])),
        total_processing_time=int(formula_data["total_processing_time"]),
        ai_explanation=formula_data.get("ai_explanation"),
        is_favorite=bool(formula_data.get("is_favorite", False)),
    )
    session.add(formula)

    for step_data in payload.formula_steps:
        session.add(
            FormulaStep(
                step_id=step_data["step_id"],
                formula_id=formula_id,
                step_order=int(step_data["step_order"]),
                zone=FormulaZone(step_data["zone"]),
                shade_id=step_data.get("shade_id"),
                developer_id=step_data.get("developer_id"),
                mixing_ratio=step_data.get("mixing_ratio"),
                quantity_grams=step_data.get("quantity_grams"),
                processing_time_minutes=step_data.get("processing_time_minutes"),
                special_instructions=step_data.get("special_instructions"),
                is_optional=bool(step_data.get("is_optional", False)),
            )
        )

    for risk_data in payload.risk_assessments:
        session.add(
            RiskAssessment(
                assessment_id=risk_data["assessment_id"],
                formula_id=formula_id,
                risk_type=RiskType(risk_data["risk_type"]),
                probability=Decimal(str(risk_data["probability"])),
                severity=RiskSeverity(risk_data["severity"]),
                contributing_factors=risk_data.get("contributing_factors") or [],
                mitigation=str(risk_data["mitigation"]),
                requires_waiver=bool(risk_data.get("requires_waiver", False)),
                waiver_text=risk_data.get("waiver_text"),
            )
        )

    session.flush()
    return formula_id


def persist_engine_output(
    session: Session,
    engine_input: EngineInput,
    output: EngineOutput,
    *,
    stylist_id: uuid.UUID = SYSTEM_STYLIST_ID,
    client_id: uuid.UUID | None = None,
    salon_id: uuid.UUID | None = None,
) -> Optional[uuid.UUID]:
    """Persist formula rows when the engine produced a persistence payload."""
    if output.persistence_payload is None:
        return None
    return persist_formula_payload(
        session,
        output.persistence_payload,
        consultation_id=engine_input.consultation_id,
        stylist_id=stylist_id,
        client_id=client_id,
        salon_id=salon_id,
    )
