"""Professional quantity planning for production formula steps."""

from __future__ import annotations

from .engine_models import EngineInput, ServiceIntent, SuggestedFormulaStep
from .production_models import FormulaZone

_BASE_GRAMS_BY_LENGTH = {
    "short": 40,
    "medium": 60,
    "long": 90,
    "extra_long": 120,
}


def hair_length_label(engine_input: EngineInput) -> str:
    """Return a supported hair-length label from engine input metadata."""
    return (engine_input.hair_length or "medium").lower()


def quantity_rationale(engine_input: EngineInput) -> str:
    """Human-readable rationale for the quantity plan."""
    label = hair_length_label(engine_input)
    base = _BASE_GRAMS_BY_LENGTH.get(label, _BASE_GRAMS_BY_LENGTH["medium"])
    if engine_input.service_intent == ServiceIntent.GLOSS_REFRESH:
        return f"{base}g total color based on {label} hair, split across refresh zones."
    return f"{base}g target color based on {label} hair; fill steps use a smaller prep amount."


def apply_quantity_plan(
    steps: list[SuggestedFormulaStep], engine_input: EngineInput
) -> list[SuggestedFormulaStep]:
    """Assign non-placeholder grams across formula steps based on service and hair length."""
    if not steps:
        return []

    label = hair_length_label(engine_input)
    base = _BASE_GRAMS_BY_LENGTH.get(label, _BASE_GRAMS_BY_LENGTH["medium"])
    fill_indices = [
        index
        for index, step in enumerate(steps)
        if step.special_instructions and step.special_instructions.startswith("Pre-fill")
    ]
    color_indices = [index for index in range(len(steps)) if index not in fill_indices]

    updates: dict[int, int] = {}
    for index in fill_indices:
        updates[index] = max(20, round(base * 0.3))

    if color_indices:
        if engine_input.service_intent == ServiceIntent.GLOSS_REFRESH and len(color_indices) >= 2:
            weights = _refresh_weights([steps[index].zone for index in color_indices])
            for index, weight in zip(color_indices, weights):
                updates[index] = max(10, round(base * weight))
        else:
            per_step = max(10, round(base / len(color_indices)))
            for index in color_indices:
                updates[index] = per_step

    return [step.model_copy(update={"quantity_grams": updates.get(index)}) for index, step in enumerate(steps)]


def _refresh_weights(zones: list[FormulaZone]) -> list[float]:
    weights = []
    for zone in zones:
        if zone == FormulaZone.ROOT:
            weights.append(0.5)
        elif zone in {FormulaZone.MID, FormulaZone.END}:
            weights.append(0.25)
        else:
            weights.append(1.0 / len(zones))
    total = sum(weights) or 1.0
    return [weight / total for weight in weights]
