"""Tests for evaluation metrics."""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nl2sql.benchmark.metrics import (
    normalize_sql,
    calculate_exact_match,
    normalize_result_rows,
    calculate_execution_accuracy,
)
from nl2sql.core.db_engine import DatabaseEngine


DB_PATH = Path(__file__).parent.parent / "data" / "benchmark_100" / "databases" / "concert_singer.sqlite"


def test_normalize_sql_case():
    n1 = normalize_sql("SELECT Name FROM singer")
    n2 = normalize_sql("select name from singer")
    assert n1 == n2


def test_normalize_sql_whitespace():
    n1 = normalize_sql("SELECT  Name   FROM   singer")
    n2 = normalize_sql("SELECT Name FROM singer")
    assert n1 == n2


def test_normalize_sql_semicolon():
    n1 = normalize_sql("SELECT Name FROM singer;")
    n2 = normalize_sql("SELECT Name FROM singer")
    assert n1 == n2


def test_exact_match_identical():
    assert calculate_exact_match("SELECT count(*) FROM singer", "SELECT count(*) FROM singer") is True


def test_exact_match_case_insensitive():
    assert calculate_exact_match("select count(*) from singer", "SELECT count(*) FROM singer") is True


def test_exact_match_different():
    assert calculate_exact_match("SELECT Name FROM singer", "SELECT count(*) FROM singer") is False


def test_exact_match_empty():
    assert calculate_exact_match("", "SELECT count(*) FROM singer") is False


def test_normalize_result_rows():
    rows = [("Alice", 30), ("Bob", 25)]
    expected = {("alice", 30), ("bob", 25)}
    result = normalize_result_rows([[r[0], r[1]] for r in rows])
    assert result == expected


def test_normalize_result_rows_float_rounding():
    rows = [[1.000000001], [2.0000099]]
    result = normalize_result_rows(rows)
    assert (1.0,) in result


@pytest.fixture
def engine():
    if not DB_PATH.exists():
        pytest.skip("Benchmark DB not found.")
    return DatabaseEngine(str(DB_PATH))


def test_execution_accuracy_same_query(engine):
    gold = "SELECT count(*) FROM singer"
    pred = "SELECT count(*) FROM singer"
    is_match, pred_res, gold_res = calculate_execution_accuracy(engine, pred, gold)
    assert is_match is True
    assert pred_res.success
    assert gold_res.success


def test_execution_accuracy_logically_equivalent(engine):
    # Both should return same set of rows
    gold = "SELECT Name FROM singer ORDER BY Age"
    pred = "SELECT Name FROM singer ORDER BY Age ASC"
    is_match, pred_res, gold_res = calculate_execution_accuracy(engine, pred, gold)
    # Result sets should match
    assert is_match is True


def test_execution_accuracy_different_queries(engine):
    gold = "SELECT count(*) FROM singer"
    pred = "SELECT count(*) FROM stadium"
    is_match, pred_res, gold_res = calculate_execution_accuracy(engine, pred, gold)
    # Different tables → different counts → not equal
    assert is_match is False


def test_execution_accuracy_failed_pred(engine):
    gold = "SELECT count(*) FROM singer"
    pred = "SELECT count(*) FROM nonexistent_xyz_table"
    is_match, pred_res, gold_res = calculate_execution_accuracy(engine, pred, gold)
    assert is_match is False
    assert not pred_res.success
