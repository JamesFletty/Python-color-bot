"""Consultation lifecycle helpers for production API/service code."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from .persist import ensure_consultation
from .production_models import Consultation, ConsultationStatus


def upsert_consultation_context(
    session: Session,
    *,
    consultation_id: uuid.UUID,
    stylist_id: uuid.UUID,
    client_id: uuid.UUID | None = None,
    salon_id: uuid.UUID | None = None,
) -> Consultation:
    """Create or update consultation identity context from authenticated request data."""
    return ensure_consultation(
        session,
        consultation_id,
        stylist_id=stylist_id,
        client_id=client_id,
        salon_id=salon_id,
    )


def update_consultation_status(
    session: Session,
    *,
    consultation_id: uuid.UUID,
    stylist_id: uuid.UUID,
    status: ConsultationStatus,
    client_id: uuid.UUID | None = None,
    salon_id: uuid.UUID | None = None,
) -> Consultation:
    """Apply a consultation lifecycle transition and preserve request identity context."""
    consultation = upsert_consultation_context(
        session,
        consultation_id=consultation_id,
        stylist_id=stylist_id,
        client_id=client_id,
        salon_id=salon_id,
    )
    consultation.status = status
    session.flush()
    return consultation


def consultation_payload(consultation: Consultation) -> dict[str, Any]:
    """Serialize a consultation row for API responses."""
    return {
        "consultation_id": consultation.consultation_id,
        "client_id": consultation.client_id,
        "stylist_id": consultation.stylist_id,
        "salon_id": consultation.salon_id,
        "status": consultation.status.value,
    }
