"""Derive Stage 13 ``selected_sub_ranges`` from shade catalog records."""

from __future__ import annotations

from typing import Any, Iterable

# Labels that do not activate collection-specific Stage 13 line rules.
_GENERIC_SUB_RANGES = frozenset({"", "Standard", "Default"})


def sub_range_labels_from_shade(sub_range: str | None) -> list[str]:
    """Return Stage 13 intake labels inferred from a shade ``sub_range`` field."""
    if not sub_range:
        return []
    cleaned = str(sub_range).strip()
    if not cleaned or cleaned in _GENERIC_SUB_RANGES:
        return []
    return [cleaned]


def merge_intake_sub_ranges(
    intake: dict[str, Any] | None,
    *,
    shade_sub_range: str | None,
) -> dict[str, Any] | None:
    """
    Inject ``selected_sub_ranges`` from the resolved shade when intake omits them.

    Explicit ``selected_sub_ranges`` on intake always win.
    """
    if intake is None:
        labels = sub_range_labels_from_shade(shade_sub_range)
        if not labels:
            return None
        return {"selected_sub_ranges": labels}

    if intake.get("selected_sub_ranges"):
        return intake

    labels = sub_range_labels_from_shade(shade_sub_range)
    if not labels:
        return intake

    merged = dict(intake)
    merged["selected_sub_ranges"] = labels
    return merged


def sub_range_labels_from_names(names: Iterable[str | None]) -> list[str]:
    """Collect unique Stage 13 sub-range labels from several shade records."""
    labels: list[str] = []
    seen: set[str] = set()
    for name in names:
        for label in sub_range_labels_from_shade(name):
            if label not in seen:
                seen.add(label)
                labels.append(label)
    return labels


def sub_range_labels_from_selected_shades(shades: Iterable[Any]) -> list[str]:
    """Collect unique labels from engine ``SelectedShade`` rows."""
    return sub_range_labels_from_names(
        getattr(shade, "sub_range_name", None) for shade in shades
    )


def sub_range_labels_from_selected_shades(shades: Iterable[Any]) -> list[str]:
    """Collect unique labels from engine ``SelectedShade`` rows."""
    return sub_range_labels_from_names(
        getattr(shade, "sub_range_name", None) for shade in shades
    )
