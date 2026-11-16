"""Tests for schema inspection utilities."""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nl2sql.core.schema_inspector import SchemaInspector


@pytest.fixture
def db_path():
    """Path to the concert_singer benchmark database."""
    p = Path(__file__).parent.parent / "data" / "benchmark_100" / "databases" / "concert_singer.sqlite"
    if not p.exists():
        pytest.skip("Benchmark database not found. Run scripts/setup_benchmark.py first.")
    return str(p)


def test_tables_loaded(db_path):
    inspector = SchemaInspector(db_path)
    tables = inspector.get_table_names()
    assert "stadium" in tables
    assert "singer" in tables
    assert "concert" in tables
    assert "singer_in_concert" in tables


def test_columns_detected(db_path):
    inspector = SchemaInspector(db_path)
    cols = inspector.get_column_names("stadium")
    assert "Name" in cols
    assert "Capacity" in cols
    assert "Stadium_ID" in cols


def test_foreign_keys_detected(db_path):
    inspector = SchemaInspector(db_path)
    concert_table = inspector.tables["concert"]
    fk_to_tables = [fk.to_table for fk in concert_table.foreign_keys]
    assert "stadium" in fk_to_tables


def test_primary_key_flag(db_path):
    inspector = SchemaInspector(db_path)
    stadium = inspector.tables["stadium"]
    pk_cols = [c for c in stadium.columns if c.is_primary_key]
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "Stadium_ID"


def test_join_path_found(db_path):
    inspector = SchemaInspector(db_path)
    path = inspector.find_shortest_join_path("singer", "concert")
    assert path is not None
    assert len(path) >= 2


def test_compact_markdown_format(db_path):
    inspector = SchemaInspector(db_path)
    md = inspector.to_compact_markdown()
    assert "stadium" in md
    assert "singer" in md
    assert "Capacity" in md


def test_ddl_string_format(db_path):
    inspector = SchemaInspector(db_path)
    ddl = inspector.to_ddl_string()
    assert "CREATE TABLE" in ddl
    assert "PRIMARY KEY" in ddl


def test_sample_values_populated(db_path):
    inspector = SchemaInspector(db_path)
    stadium = inspector.tables["stadium"]
    # At least one column should have sample values
    has_samples = any(c.sample_values for c in stadium.columns)
    assert has_samples
