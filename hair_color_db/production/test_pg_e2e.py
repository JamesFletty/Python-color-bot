"""End-to-end PostgreSQL integration tests (require DATABASE_URL)."""

from __future__ import annotations

import os
import unittest
import uuid

from sqlalchemy import func, select

from hair_color_db.production.bootstrap import bootstrap_database
from hair_color_db.production.catalog_lookup import resolve_catalog_reference
from hair_color_db.production.db import create_db_engine, create_session_factory
from hair_color_db.production.engine_models import EngineInput, SelectedShade, ServiceIntent
from hair_color_db.production.formula_builder import run_engine
from hair_color_db.production.import_stage12_research import DEFAULT_SUB_RANGE, _sub_range_id
from hair_color_db.production.persist import persist_engine_output
from hair_color_db.production.production_models import (
    Formula,
    FormulaStep,
    HairTexture,
    ShadeIntermixingRule,
)
from hair_color_db.production.repositories import SqlAlchemyEngineRepository
from hair_color_db.production.run_production_engine import run_production_engine
from src.paths import EXPECTED_SHADE_COUNT


class PostgreSqlEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not os.environ.get("DATABASE_URL"):
            raise unittest.SkipTest("DATABASE_URL not set; PostgreSQL e2e skipped")
        cls.engine = create_db_engine()
        cls.Session = create_session_factory(cls.engine)
        with cls.Session() as session:
            cls.bootstrap = bootstrap_database(session, engine=cls.engine)
            session.commit()

    def test_bootstrap_imports_full_catalog(self) -> None:
        report = self.bootstrap.stage12_report
        self.assertEqual(report["shade_count"], EXPECTED_SHADE_COUNT)
        self.assertTrue(report["shade_count_ok"])
        self.assertGreater(self.bootstrap.stage13.get("universal_rules", 0), 0)

    def test_intermixing_rules_loaded(self) -> None:
        # Seeds are INSERT...SELECT against research tables, so they only populate
        # after the Stage 12 import runs (regression for the migration-time no-op).
        with self.Session() as session:
            count = session.scalar(select(func.count()).select_from(ShadeIntermixingRule)) or 0
        self.assertGreater(count, 0)

    def test_intermixing_blocks_incompatible_sub_ranges(self) -> None:
        canonical = "Matrix::SoColor::US"
        with self.Session() as session:
            ten_min = resolve_catalog_reference(
                session,
                canonical_key=canonical,
                shade_code="504N",
                sub_range_name="Pre-Bonded 10 min",
            )
            standard = resolve_catalog_reference(
                session,
                canonical_key=canonical,
                shade_code="5N",
                sub_range_name=DEFAULT_SUB_RANGE,
            )
            result = run_engine(
                EngineInput(
                    consultation_id=uuid.uuid4(),
                    line_id=ten_min.line_id,
                    brand_id=ten_min.brand_id,
                    line_region_id=ten_min.line_region_id,
                    natural_level=5,
                    existing_level=5,
                    porosity=5,
                    elasticity=6,
                    gray_percentage=20,
                    texture=HairTexture.MEDIUM,
                    desired_result="deposit",
                    desired_level=5,
                    service_intent=ServiceIntent.TONE_DEPOSIT,
                    selected_shades=[
                        SelectedShade(
                            shade_id=ten_min.shade_id,
                            shade_code="504N",
                            sub_range_id=_sub_range_id(canonical, "Pre-Bonded 10 min"),
                        ),
                        SelectedShade(
                            shade_id=standard.shade_id,
                            shade_code="5N",
                            sub_range_id=_sub_range_id(canonical, DEFAULT_SUB_RANGE),
                        ),
                    ],
                ),
                SqlAlchemyEngineRepository(session),
                line_region_id=ten_min.line_region_id,
            )
        self.assertEqual(result.recommendation_status.value, "blocked")
        self.assertTrue(any("10 min" in reason for reason in result.blocked_by))

    def test_sqlalchemy_repository_runs_engine(self) -> None:
        with self.Session() as session:
            catalog = resolve_catalog_reference(
                session,
                canonical_key="Matrix::SoColor::US",
                shade_code="5N",
            )
            result = run_engine(
                EngineInput(
                    consultation_id=uuid.uuid4(),
                    line_id=catalog.line_id,
                    brand_id=catalog.brand_id,
                    line_region_id=catalog.line_region_id,
                    natural_level=5,
                    existing_level=5,
                    porosity=5,
                    elasticity=6,
                    gray_percentage=60,
                    texture=HairTexture.MEDIUM,
                    desired_result="gray coverage brunette",
                    desired_level=5,
                    service_intent=ServiceIntent.GRAY_COVERAGE,
                    selected_shades=[
                        SelectedShade(
                            shade_id=catalog.shade_id,
                            shade_code=catalog.shade_code,
                        )
                    ],
                ),
                SqlAlchemyEngineRepository(session),
                line_region_id=catalog.line_region_id,
            )
        self.assertIn(result.recommendation_status.value, {"ok", "caution"})
        self.assertGreater(len(result.matched_rules), 0)
        self.assertGreater(len(result.suggested_formula), 0)

    def test_persist_formula_round_trip(self) -> None:
        consultation_id = uuid.uuid4()
        with self.Session() as session:
            catalog = resolve_catalog_reference(
                session,
                canonical_key="Matrix::SoColor::US",
                shade_code="5N",
            )
            engine_input = EngineInput(
                consultation_id=consultation_id,
                line_id=catalog.line_id,
                brand_id=catalog.brand_id,
                line_region_id=catalog.line_region_id,
                natural_level=5,
                existing_level=5,
                porosity=5,
                elasticity=6,
                gray_percentage=20,
                texture=HairTexture.MEDIUM,
                desired_result="rich brunette",
                desired_level=5,
                service_intent=ServiceIntent.TONE_DEPOSIT,
                selected_shades=[
                    SelectedShade(
                        shade_id=catalog.shade_id,
                        shade_code=catalog.shade_code,
                    )
                ],
            )
            payload_result = run_production_engine(
                session,
                engine_input,
                line_region_id=catalog.line_region_id,
                persist=True,
            )
            self.assertTrue(payload_result["persisted"])
            formula_id = uuid.UUID(str(payload_result["formula_id"]))
            step_count = session.scalar(
                select(func.count())
                .select_from(FormulaStep)
                .where(FormulaStep.formula_id == formula_id)
            )
            formula = session.get(Formula, formula_id)
        self.assertIsNotNone(formula)
        self.assertEqual(formula.consultation_id, consultation_id)
        self.assertIsNotNone(step_count)


if __name__ == "__main__":
    unittest.main()
