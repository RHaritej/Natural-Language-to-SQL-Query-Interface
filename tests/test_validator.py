"""Tests for SQL validation."""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nl2sql.core.validator import SQLValidator
from nl2sql.core.schema_inspector import SchemaInspector


@pytest.fixture
def inspector():
    p = Path(__file__).parent.parent / "data" / "benchmark_100" / "databases" / "concert_singer.sqlite"
    if not p.exists():
        pytest.skip("Benchmark database not found. Run setup_benchmark.py first.")
    return SchemaInspector(str(p))


@pytest.fixture
def validator(inspector):
    return SQLValidator(inspector=inspector)


def test_valid_simple_select(validator):
    result = validator.validate("SELECT Name FROM singer")
    assert result.is_valid
    assert result.syntax_error is None


def test_valid_join(validator):
    result = validator.validate(
        "SELECT T1.Name, T2.concert_Name FROM stadium T1 JOIN concert T2 ON T1.Stadium_ID = T2.Stadium_ID"
    )
    assert result.is_valid


def test_valid_aggregate(validator):
    result = validator.validate("SELECT avg(Age) FROM singer")
    assert result.is_valid


def test_invalid_nonexistent_table(validator):
    result = validator.validate("SELECT * FROM nonexistent_table_xyz")
    assert not result.is_valid
    assert len(result.schema_errors) > 0


def test_disallowed_delete(validator):
    result = validator.validate("DELETE FROM singer")
    assert not result.is_valid


def test_disallowed_drop(validator):
    result = validator.validate("DROP TABLE singer")
    assert not result.is_valid


def test_markdown_fence_stripping(validator):
    sql_with_fence = "```sql\nSELECT Name FROM singer\n```"
    cleaned = validator.clean_markdown_fences(sql_with_fence)
    assert "```" not in cleaned
    assert "SELECT" in cleaned


def test_markdown_code_block_no_sql_prefix(validator):
    sql_with_fence = "```\nSELECT * FROM stadium\n```"
    cleaned = validator.clean_markdown_fences(sql_with_fence)
    assert "```" not in cleaned


def test_cte_query_valid(validator):
    cte_sql = """
    WITH top_stadiums AS (
        SELECT Stadium_ID, Name FROM stadium WHERE Capacity > 5000
    )
    SELECT * FROM top_stadiums
    """
    result = validator.validate(cte_sql)
    assert result.is_valid


def test_subquery_valid(validator):
    sql = "SELECT Name FROM singer WHERE Age > (SELECT avg(Age) FROM singer)"
    result = validator.validate(sql)
    assert result.is_valid


def test_normalized_sql_returned(validator):
    sql = "select   name  from   singer   where age > 20"
    result = validator.validate(sql)
    assert result.normalized_sql is not None
    assert "SELECT" in result.normalized_sql.upper()
