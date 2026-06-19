"""Data access layer for the deterministic formula engine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .import_stage13_rules import LineScope, build_formulation_rules_from_stage13
from .production_models import (
    FormulationRule,
    FormulationRuleBrand,
    FormulationRuleLine,
    LineTechnicalRule,
    ProductLine,
    ProductLineRegion,
    ShadeIntermixingRule,
    UniversalColorScience,
)


@dataclass
class FormulationRuleRecord:
    rule_id: UUID
    rule_name: str
    rule_priority: int
    rule_condition: dict[str, Any]
    rule_action: dict[str, Any]
    rule_category: str
    brand_ids: list[UUID] = field(default_factory=list)
    line_ids: list[UUID] = field(default_factory=list)
    scope_level: str = "universal"


@dataclass
class LineTechnicalRuleRecord:
    rule_id: UUID
    line_region_id: UUID
    rule_type: str
    rule_value: Optional[dict[str, Any]]
    applies_to_sub_range_id: Optional[UUID]
    developer_volume: Optional[int] = None
    max_lift_levels: Optional[float] = None
    gray_coverage_pct: Optional[int] = None
    mixing_ratio_num: Optional[int] = None
    mixing_ratio_den: Optional[int] = None
    processing_time_min: Optional[int] = None
    applicable_hair_type: Optional[list[str]] = None
    porosity_adjustment: Optional[dict[str, Any]] = None


@dataclass
class IntermixingRuleRecord:
    rule_id: UUID
    line_region_id: Optional[UUID]
    applies_to_sub_range_id: Optional[UUID]
    compatible_sub_range_id: Optional[UUID]
    shade_id: Optional[UUID]
    compatible_shade_id: Optional[UUID]
    rule_scope: str
    restriction_type: str
    restriction_note: str


@dataclass
class UniversalColorScienceRecord:
    level: int
    underlying_pigment: Optional[str]
    neutralizing_tone: Optional[str]
    neutralizing_tone_id: Optional[UUID]
    exposure_stage: Optional[str]
    confidence: str


class EngineRepository(Protocol):
    """Repository boundary for FastAPI / service integration."""

    def get_brand_id_for_line(self, line_id: UUID) -> Optional[UUID]: ...

    def load_active_formulation_rules(
        self, brand_id: Optional[UUID], line_id: UUID
    ) -> list[FormulationRuleRecord]: ...

    def load_line_technical_rules(
        self, line_region_id: UUID, sub_range_id: Optional[UUID] = None
    ) -> list[LineTechnicalRuleRecord]: ...

    def load_intermixing_rules(
        self, line_region_id: UUID
    ) -> list[IntermixingRuleRecord]: ...

    def load_universal_color_science(self) -> list[UniversalColorScienceRecord]: ...

    def enrich_fill_guidance(
        self, line_region_id: UUID | None, fill_guidance: dict[str, Any] | None
    ) -> dict[str, Any] | None: ...


class InMemoryEngineRepository:
    """In-memory repository for unit tests and offline evaluation."""

    def __init__(
        self,
        *,
        brand_id_by_line: dict[UUID, UUID],
        formulation_rules: list[FormulationRuleRecord],
        line_technical_rules: list[LineTechnicalRuleRecord],
        intermixing_rules: list[IntermixingRuleRecord],
        color_science: list[UniversalColorScienceRecord],
    ) -> None:
        self.brand_id_by_line = brand_id_by_line
        self.formulation_rules = formulation_rules
        self.line_technical_rules = line_technical_rules
        self.intermixing_rules = intermixing_rules
        self.color_science = color_science

    def get_brand_id_for_line(self, line_id: UUID) -> Optional[UUID]:
        return self.brand_id_by_line.get(line_id)

    def load_active_formulation_rules(
        self, brand_id: Optional[UUID], line_id: UUID
    ) -> list[FormulationRuleRecord]:
        applicable: list[FormulationRuleRecord] = []
        for rule in self.formulation_rules:
            if rule.scope_level == "line":
                if rule.line_ids and line_id in rule.line_ids:
                    applicable.append(rule)
                continue
            if rule.line_ids:
                if line_id in rule.line_ids:
                    applicable.append(rule)
            elif rule.brand_ids:
                if brand_id and brand_id in rule.brand_ids:
                    applicable.append(rule)
            else:
                applicable.append(rule)
        return applicable

    def load_line_technical_rules(
        self, line_region_id: UUID, sub_range_id: Optional[UUID] = None
    ) -> list[LineTechnicalRuleRecord]:
        rules = [
            r
            for r in self.line_technical_rules
            if r.line_region_id == line_region_id
            and (r.applies_to_sub_range_id is None or r.applies_to_sub_range_id == sub_range_id)
        ]
        return rules

    def load_intermixing_rules(self, line_region_id: UUID) -> list[IntermixingRuleRecord]:
        return [r for r in self.intermixing_rules if r.line_region_id == line_region_id]

    def load_universal_color_science(self) -> list[UniversalColorScienceRecord]:
        return list(self.color_science)

    def enrich_fill_guidance(
        self, line_region_id: UUID | None, fill_guidance: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        return fill_guidance


class SqlAlchemyEngineRepository:
    """SQLAlchemy-backed repository for production persistence."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_brand_id_for_line(self, line_id: UUID) -> Optional[UUID]:
        line = self.session.get(ProductLine, line_id)
        return line.brand_id if line else None

    def load_active_formulation_rules(
        self, brand_id: Optional[UUID], line_id: UUID
    ) -> list[FormulationRuleRecord]:
        rules = self.session.scalars(
            select(FormulationRule).where(FormulationRule.is_active.is_(True))
        ).all()
        records: list[FormulationRuleRecord] = []
        for rule in rules:
            brand_ids = [link.brand_id for link in rule.brand_links]
            line_ids = [link.line_id for link in rule.line_links]
            if rule.scope_level == "line":
                if line_ids and line_id in line_ids:
                    pass
                else:
                    continue
            elif line_ids:
                if line_id not in line_ids:
                    continue
            elif brand_ids:
                if not brand_id or brand_id not in brand_ids:
                    continue
            records.append(
                FormulationRuleRecord(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    rule_priority=rule.rule_priority,
                    rule_condition=dict(rule.rule_condition),
                    rule_action=dict(rule.rule_action),
                    rule_category=rule.rule_category.value,
                    brand_ids=brand_ids,
                    line_ids=line_ids,
                    scope_level=rule.scope_level,
                )
            )
        return records

    def load_line_technical_rules(
        self, line_region_id: UUID, sub_range_id: Optional[UUID] = None
    ) -> list[LineTechnicalRuleRecord]:
        stmt = select(LineTechnicalRule).where(
            LineTechnicalRule.line_region_id == line_region_id
        )
        rows = self.session.scalars(stmt).all()
        records: list[LineTechnicalRuleRecord] = []
        for row in rows:
            if row.applies_to_sub_range_id and sub_range_id:
                if row.applies_to_sub_range_id != sub_range_id:
                    continue
            records.append(
                LineTechnicalRuleRecord(
                    rule_id=row.rule_id,
                    line_region_id=row.line_region_id,
                    rule_type=row.rule_type,
                    rule_value=row.rule_value,
                    applies_to_sub_range_id=row.applies_to_sub_range_id,
                    developer_volume=row.developer_volume,
                    max_lift_levels=float(row.max_lift_levels)
                    if row.max_lift_levels is not None
                    else None,
                    gray_coverage_pct=row.gray_coverage_pct,
                    mixing_ratio_num=row.mixing_ratio_num,
                    mixing_ratio_den=row.mixing_ratio_den,
                    processing_time_min=row.processing_time_min,
                    applicable_hair_type=row.applicable_hair_type,
                    porosity_adjustment=row.porosity_adjustment,
                )
            )
        return records

    def load_intermixing_rules(self, line_region_id: UUID) -> list[IntermixingRuleRecord]:
        rows = self.session.scalars(
            select(ShadeIntermixingRule).where(
                ShadeIntermixingRule.line_region_id == line_region_id
            )
        ).all()
        return [
            IntermixingRuleRecord(
                rule_id=row.rule_id,
                line_region_id=row.line_region_id,
                applies_to_sub_range_id=row.applies_to_sub_range_id,
                compatible_sub_range_id=row.compatible_sub_range_id,
                shade_id=row.shade_id,
                compatible_shade_id=row.compatible_shade_id,
                rule_scope=row.rule_scope.value,
                restriction_type=row.restriction_type.value,
                restriction_note=row.restriction_note,
            )
            for row in rows
        ]

    def load_universal_color_science(self) -> list[UniversalColorScienceRecord]:
        rows = self.session.scalars(select(UniversalColorScience)).all()
        return [
            UniversalColorScienceRecord(
                level=row.level,
                underlying_pigment=row.underlying_pigment,
                neutralizing_tone=row.neutralizing_tone,
                neutralizing_tone_id=row.neutralizing_tone_id,
                exposure_stage=row.exposure_stage,
                confidence=row.confidence.value,
            )
            for row in rows
        ]

    def enrich_fill_guidance(
        self, line_region_id: UUID | None, fill_guidance: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if line_region_id is None or not fill_guidance:
            return fill_guidance
        region = self.session.get(ProductLineRegion, line_region_id)
        if region is None:
            return fill_guidance
        from .fill_shade_lookup import enrich_fill_guidance_with_inventory

        return enrich_fill_guidance_with_inventory(
            self.session,
            region.canonical_key,
            fill_guidance,
        )


def build_seed_repository() -> InMemoryEngineRepository:
    """Repository preloaded from Stage 13 import logic + Matrix intermixing fixtures."""
    matrix_brand = uuid.UUID("00000000-0000-4000-8000-000000000001")
    matrix_line = uuid.UUID("00000000-0000-4000-8000-000000000010")
    matrix_region = uuid.UUID("00000000-0000-4000-8000-000000000100")
    hd_sub = uuid.UUID("00000000-0000-4000-8000-000000000201")
    ultra_sub = uuid.UUID("00000000-0000-4000-8000-000000000202")
    dreamage_sub = uuid.UUID("00000000-0000-4000-8000-000000000204")
    ten_min_sub = uuid.UUID("00000000-0000-4000-8000-000000000205")

    rules = build_formulation_rules_from_stage13(
        line_mapping={
            "Matrix::SoColor::US": LineScope(brand_id=matrix_brand, line_id=matrix_line),
        }
    )

    intermixing = [
        IntermixingRuleRecord(
            rule_id=uuid.uuid4(),
            line_region_id=matrix_region,
            applies_to_sub_range_id=hd_sub,
            compatible_sub_range_id=None,
            shade_id=None,
            compatible_shade_id=None,
            rule_scope="sub_range_isolated_from_line",
            restriction_type="not_mixable",
            restriction_note="HD Series not mixable with any other SoColor shade.",
        ),
        IntermixingRuleRecord(
            rule_id=uuid.uuid4(),
            line_region_id=matrix_region,
            applies_to_sub_range_id=ultra_sub,
            compatible_sub_range_id=None,
            shade_id=None,
            compatible_shade_id=None,
            rule_scope="sub_range_isolated_from_line",
            restriction_type="not_mixable",
            restriction_note="Ultra Blonde not intermixable with other SoColor shades.",
        ),
        IntermixingRuleRecord(
            rule_id=uuid.uuid4(),
            line_region_id=matrix_region,
            applies_to_sub_range_id=dreamage_sub,
            compatible_sub_range_id=None,
            shade_id=None,
            compatible_shade_id=None,
            rule_scope="cross_sub_range",
            restriction_type="caution",
            restriction_note="DreamAge mixing with non-DreamAge not recommended.",
        ),
        IntermixingRuleRecord(
            rule_id=uuid.uuid4(),
            line_region_id=matrix_region,
            applies_to_sub_range_id=ten_min_sub,
            compatible_sub_range_id=None,
            shade_id=None,
            compatible_shade_id=None,
            rule_scope="sub_range_internal_only",
            restriction_type="not_mixable",
            restriction_note="SoColor 10 min only mixable with other 10 min shades.",
        ),
    ]

    color_science = [
        UniversalColorScienceRecord(6, "Orange", "Blue", None, "Mid lift", "established"),
        UniversalColorScienceRecord(9, "Yellow", "Violet", None, "High lift", "established"),
        UniversalColorScienceRecord(10, "Pale yellow", "Violet/Ash", None, "Pale stage", "established"),
    ]

    line_technical = [
        LineTechnicalRuleRecord(
            rule_id=uuid.uuid4(),
            line_region_id=matrix_region,
            rule_type="developer",
            rule_value=None,
            applies_to_sub_range_id=None,
            developer_volume=20,
            processing_time_min=35,
            mixing_ratio_num=1,
            mixing_ratio_den=1,
        )
    ]

    return InMemoryEngineRepository(
        brand_id_by_line={matrix_line: matrix_brand},
        formulation_rules=rules,
        line_technical_rules=line_technical,
        intermixing_rules=intermixing,
        color_science=color_science,
    )


# Export stable test IDs used by golden-path fixtures.
MATRIX_BRAND_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
MATRIX_LINE_ID = uuid.UUID("00000000-0000-4000-8000-000000000010")
MATRIX_REGION_ID = uuid.UUID("00000000-0000-4000-8000-000000000100")
HD_SUB_RANGE_ID = uuid.UUID("00000000-0000-4000-8000-000000000201")
ULTRA_BLONDE_SUB_RANGE_ID = uuid.UUID("00000000-0000-4000-8000-000000000202")
BLENDED_SUB_RANGE_ID = uuid.UUID("00000000-0000-4000-8000-000000000203")
DREAMAGE_SUB_RANGE_ID = uuid.UUID("00000000-0000-4000-8000-000000000204")
TEN_MIN_SUB_RANGE_ID = uuid.UUID("00000000-0000-4000-8000-000000000205")
NORMAL_SUB_RANGE_ID = uuid.UUID("00000000-0000-4000-8000-000000000206")
