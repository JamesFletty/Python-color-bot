"""Tests for PostgreSQL migration statement splitting."""

from __future__ import annotations

import unittest
from pathlib import Path

from .migrate import _alembic_config, _statements


class MigrationStatementTests(unittest.TestCase):
    def test_statements_preserve_dollar_quoted_function_body(self) -> None:
        sql = """
        CREATE FUNCTION set_updated_at()
        RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TABLE sample (id integer primary key);
        """

        statements = _statements(sql)

        self.assertEqual(len(statements), 2)
        self.assertIn("NEW.updated_at = now();", statements[0])
        self.assertTrue(statements[0].endswith("LANGUAGE plpgsql"))
        self.assertEqual(statements[1], "CREATE TABLE sample (id integer primary key)")

    def test_statements_ignore_semicolons_in_strings_and_comments(self) -> None:
        sql = """
        -- comment with ;
        INSERT INTO sample (name) VALUES ('semi;colon');
        /* block ; comment */
        SELECT "weird;identifier" FROM sample;
        """

        statements = _statements(sql)

        self.assertEqual(len(statements), 2)
        self.assertIn("'semi;colon'", statements[0])
        self.assertIn('"weird;identifier"', statements[1])

    def test_alembic_config_points_to_packaged_project(self) -> None:
        config = _alembic_config(database_url="postgresql+psycopg2://example/example")
        script_location = Path(config.get_main_option("script_location"))

        self.assertEqual(script_location.name, "alembic")
        self.assertTrue((script_location / "env.py").exists())
        self.assertEqual(
            config.get_main_option("sqlalchemy.url"),
            "postgresql+psycopg2://example/example",
        )


if __name__ == "__main__":
    unittest.main()
