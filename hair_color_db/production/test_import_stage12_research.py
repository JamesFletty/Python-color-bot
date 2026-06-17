"""Tests for Stage 12 research import pipeline."""

from __future__ import annotations

import os
import unittest
import uuid

from hair_color_db.production.engine_models import EngineInput, SelectedShade, ServiceIntent
from hair_color_db.production.formula_builder import run_engine
from hair_color_db.production.import_stage12_research import (
    DEFAULT_SUB_RANGE,
    STAGE12_BATCH_LABEL,
    _brand_id,
    _line_id,
    _region_id,
    _shade_id,
    deterministic_id,
    import_stage12_research,
    validate_import_counts,
)
from hair_color_db.production.import_stage13_rules import LineScope, build_formulation_rules_from_stage13
from hair_color_db.production.production_models import (
    Base,
    Brand,
    HairTexture,
    IngestionRun,
    LineTechnicalRule,
    NormalizedTone,
    ProductLine,
    ProductLineRegion,
    Shade,
    ShadeRaw,
    SourceDocument,
    SubRange,
    ToneCodeReference,
    ToneNormalization,
)
from hair_color_db.production.repositories import (
    InMemoryEngineRepository,
    UniversalColorScienceRecord,
)
from src.loaders import load_json
from src.paths import EXPECTED_SHADE_COUNT, EXPECTED_TONE_MAPPING_COUNT, SHADES_JSON, TONE_MAP_JSON


_RESEARCH_TABLES = [
    Brand.__table__,
    ProductLine.__table__,
    ProductLineRegion.__table__,
    SubRange.__table__,
    IngestionRun.__table__,
    SourceDocument.__table__,
    ShadeRaw.__table__,
    Shade.__table__,
    NormalizedTone.__table__,
    ToneCodeReference.__table__,
    ToneNormalization.__table__,
    LineTechnicalRule.__table__,
]


class Stage12ImportUnitTests(unittest.TestCase):
    def test_json_artifact_counts(self) -> None:
        shades = load_json(SHADES_JSON)
        tones = load_json(TONE_MAP_JSON)
        self.assertEqual(len(shades["normalized_shade_records"]), EXPECTED_SHADE_COUNT)
        self.assertEqual(len(tones["tone_normalization_map"]), EXPECTED_TONE_MAPPING_COUNT)

    def test_deterministic_ids_are_stable(self) -> None:
        first = _shade_id("Matrix::SoColor::US", DEFAULT_SUB_RANGE, "5NN")
        second = _shade_id("Matrix::SoColor::US", DEFAULT_SUB_RANGE, "5NN")
        self.assertEqual(first, second)
        self.assertEqual(deterministic_id("x"), deterministic_id("x"))

    def test_batch_label_constant(self) -> None:
        self.assertEqual(STAGE12_BATCH_LABEL, "stage12_package_v1")


class Stage12ImportIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not os.environ.get("DATABASE_URL"):
            raise unittest.SkipTest("DATABASE_URL not set; PostgreSQL integration skipped")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        cls.engine = create_engine(os.environ["DATABASE_URL"])
        Base.metadata.create_all(cls.engine, tables=_RESEARCH_TABLES)
        cls.Session = sessionmaker(bind=cls.engine)
        with cls.Session() as session:
            cls.summary = import_stage12_research(session)
            cls.report = validate_import_counts(
                session, tone_mappings_imported=cls.summary.tone_mappings
            )
            session.commit()

    def test_import_produces_expected_shade_count(self) -> None:
        self.assertEqual(self.report["shade_count"], EXPECTED_SHADE_COUNT)
        self.assertTrue(self.report["shade_count_ok"])

    def test_import_produces_expected_tone_mapping_count(self) -> None:
        self.assertEqual(self.report["tone_mapping_count"], EXPECTED_TONE_MAPPING_COUNT)
        self.assertTrue(self.report["tone_mapping_count_ok"])

    def test_import_is_idempotent(self) -> None:
        with self.Session() as session:
            import_stage12_research(session)
            report = validate_import_counts(session)
            session.commit()
        self.assertEqual(report["shade_count"], EXPECTED_SHADE_COUNT)

    def test_matrix_socolor_5n_deterministic_shade_id(self) -> None:
        shade_id = _shade_id("Matrix::SoColor::US", DEFAULT_SUB_RANGE, "5N")
        with self.Session() as session:
            from sqlalchemy import select

            row = session.scalar(select(Shade.shade_id).where(Shade.shade_id == shade_id))
        self.assertEqual(row, shade_id)


class Stage12EngineEndToEndTests(unittest.TestCase):
    def test_run_engine_with_imported_catalog_shade_uuid(self) -> None:
        """run_engine accepts shade UUIDs produced by the Stage 12 import."""
        canonical_key = "Matrix::SoColor::US"
        shade_id = _shade_id(canonical_key, DEFAULT_SUB_RANGE, "5NN")
        line_id = _line_id("Matrix", "SoColor")
        brand_id = _brand_id("Matrix")
        region_id = _region_id(canonical_key)
        rules = build_formulation_rules_from_stage13(
            line_mapping={canonical_key: LineScope(brand_id=brand_id, line_id=line_id)}
        )
        repo = InMemoryEngineRepository(
            brand_id_by_line={line_id: brand_id},
            formulation_rules=rules,
            line_technical_rules=[],
            intermixing_rules=[],
            color_science=[
                UniversalColorScienceRecord(
                    6, "Orange", "Blue", None, "Mid lift", "established"
                )
            ],
        )

        result = run_engine(
            EngineInput(
                consultation_id=uuid.uuid4(),
                line_id=line_id,
                brand_id=brand_id,
                line_region_id=region_id,
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
                        shade_id=shade_id,
                        shade_code="5NN",
                    )
                ],
            ),
            repo,
            line_region_id=region_id,
        )
        self.assertIn(
            result.recommendation_status.value,
            {"ok", "caution"},
        )
        self.assertGreater(len(result.matched_rules), 0)


if __name__ == "__main__":
    unittest.main()
