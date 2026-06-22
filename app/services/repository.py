"""Data access for the v2 deterministic formula engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Brand, FormulationRule, ProductLine, Shade, ShadeTone


@dataclass
class FormulationRuleRecord:
    rule_id: str
    rule_name: str
    rule_priority: int
    rule_condition: dict[str, Any]
    rule_action: dict[str, Any]
    rule_category: str
    line_id: int | None = None
    scope_level: str = "universal"
    evidence_status: str | None = None


class EngineRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_brand_id_for_line(self, line_id: int) -> int | None:
        line = self.session.get(ProductLine, line_id)
        return line.brand_id if line else None

    def load_active_formulation_rules(
        self, brand_id: int | None, line_id: int
    ) -> list[FormulationRuleRecord]:
        rows = self.session.scalars(
            select(FormulationRule)
            .where(FormulationRule.is_active.is_(True))
            .where(FormulationRule.is_dormant.is_(False))
            .order_by(FormulationRule.rule_priority)
        ).all()

        records: list[FormulationRuleRecord] = []
        for rule in rows:
            if rule.scope_level == "line":
                if rule.line_id != line_id:
                    continue
            elif rule.line_id is not None and rule.line_id != line_id:
                continue
            records.append(
                FormulationRuleRecord(
                    rule_id=rule.package_rule_id,
                    rule_name=rule.rule_name,
                    rule_priority=rule.rule_priority,
                    rule_condition=dict(rule.rule_condition),
                    rule_action=dict(rule.rule_action),
                    rule_category=rule.rule_category,
                    line_id=rule.line_id,
                    scope_level=rule.scope_level,
                    evidence_status=rule.evidence_status,
                )
            )
        return records

    def get_line_by_canonical_key(self, canonical_key: str) -> ProductLine | None:
        return self.session.scalar(
            select(ProductLine).where(ProductLine.canonical_key == canonical_key)
        )

    def get_shade_with_line(self, shade_id: int) -> Shade | None:
        return self.session.scalar(
            select(Shade)
            .options(joinedload(Shade.line).joinedload(ProductLine.brand), joinedload(Shade.tones))
            .where(Shade.shade_id == shade_id)
        )

    def find_shades_by_code(
        self,
        shade_code: str,
        *,
        brand_hint: str | None = None,
        line_hint: str | None = None,
    ) -> list[Shade]:
        stmt = (
            select(Shade)
            .join(ProductLine, ProductLine.line_id == Shade.line_id)
            .join(Brand, Brand.brand_id == ProductLine.brand_id)
            .options(joinedload(Shade.line).joinedload(ProductLine.brand), joinedload(Shade.tones))
            .where(Shade.shade_code == shade_code)
            .where(Shade.discontinued.is_(False))
        )
        if brand_hint:
            stmt = stmt.where(Brand.brand_name.ilike(f"%{brand_hint}%"))
        if line_hint:
            stmt = stmt.where(
                or_(
                    ProductLine.line_name.ilike(f"%{line_hint}%"),
                    ProductLine.canonical_key.ilike(f"%{line_hint}%"),
                )
            )
        return list(self.session.scalars(stmt).unique().all())

    @staticmethod
    def shade_to_resolved(shade: Shade) -> dict[str, Any]:
        line = shade.line
        brand = line.brand if line else None
        return {
            "shade_id": shade.shade_id,
            "shade_code": shade.shade_code,
            "shade_name": shade.shade_name,
            "level": float(shade.level) if shade.level is not None else None,
            "brand": brand.brand_name if brand else "",
            "product_line": line.line_name if line else "",
            "line_id": shade.line_id,
            "canonical_key": line.canonical_key if line else "",
            "sub_range": shade.sub_range,
            "normalized_tones": [tone.tone_name for tone in shade.tones],
            "mixing_ratio": shade.mixing_ratio,
            "color_type": shade.color_type,
            "gray_coverage_claim": shade.gray_coverage_claim,
        }
