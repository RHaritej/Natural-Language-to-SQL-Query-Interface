"""Tests for SQL generation strategies using the MockLLMClient."""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nl2sql.core.schema_inspector import SchemaInspector
from nl2sql.llm.mock_client import MockLLMClient
from nl2sql.generators.zero_shot import ZeroShotSQLGenerator
from nl2sql.generators.few_shot import FewShotSQLGenerator
from nl2sql.generators.cot_planner import CoTPlannerSQLGenerator


DB_PATH = Path(__file__).parent.parent / "data" / "benchmark_100" / "databases" / "concert_singer.sqlite"


@pytest.fixture
def inspector():
    if not DB_PATH.exists():
        pytest.skip("Benchmark DB not set up. Run setup_benchmark.py.")
    return SchemaInspector(str(DB_PATH))


@pytest.fixture
def mock_llm():
    client = MockLLMClient()
    client.register_gold_queries({
        "how many singers do we have?": "SELECT count(*) FROM singer",
        "what are all the names and countries of singers?": "SELECT Name, Country FROM singer",
        "what is the average age of all singers?": "SELECT avg(Age) FROM singer",
    })
    return client


def test_zero_shot_generation(inspector, mock_llm):
    gen = ZeroShotSQLGenerator(inspector=inspector, llm=mock_llm)
    result = gen.generate("How many singers do we have?")
    assert result.strategy == "zero_shot"
    assert result.generated_sql != ""
    assert result.validation is not None


def test_few_shot_generation(inspector, mock_llm):
    gen = FewShotSQLGenerator(inspector=inspector, llm=mock_llm)
    result = gen.generate("What is the average age of all singers?")
    assert result.strategy == "few_shot"
    assert "avg" in result.generated_sql.lower() or "AVG" in result.generated_sql


def test_cot_planner_generation(inspector, mock_llm):
    gen = CoTPlannerSQLGenerator(inspector=inspector, llm=mock_llm)
    result = gen.generate("How many singers do we have?")
    assert result.strategy == "cot_planner"
    assert result.query_plan is not None
    assert len(result.query_plan.cot_reasoning_steps) > 0


def test_query_plan_tables_identified(inspector, mock_llm):
    from nl2sql.core.query_planner import QueryPlanner
    planner = QueryPlanner(inspector=inspector)
    plan = planner.plan("How many singers are from the United States?")
    # singer table should be identified
    assert any("singer" in t.lower() for t in plan.relevant_tables)


def test_cot_plan_aggregation_detected(inspector, mock_llm):
    from nl2sql.core.query_planner import QueryPlanner
    planner = QueryPlanner(inspector=inspector)
    plan = planner.plan("How many stadiums are there?")
    assert len(plan.aggregations) > 0
    assert plan.aggregations[0].function == "COUNT"


def test_subquery_detection_above_average(inspector, mock_llm):
    from nl2sql.core.query_planner import QueryPlanner
    planner = QueryPlanner(inspector=inspector)
    plan = planner.plan("Find singers with age more than average.")
    assert any(sq.subquery_type == "AGGREGATE_COMPARISON" for sq in plan.subqueries)


def test_subquery_detection_exclusion(inspector, mock_llm):
    from nl2sql.core.query_planner import QueryPlanner
    planner = QueryPlanner(inspector=inspector)
    plan = planner.plan("Find stadiums that never hosted a concert.")
    assert any(sq.subquery_type == "EXCLUSION_NOT_IN" for sq in plan.subqueries)


def test_prompt_includes_schema(inspector, mock_llm):
    gen = ZeroShotSQLGenerator(inspector=inspector, llm=mock_llm)
    prompt = gen.build_prompt("How many singers do we have?")
    assert "singer" in prompt
    assert "stadium" in prompt


def test_generation_result_has_validation(inspector, mock_llm):
    gen = ZeroShotSQLGenerator(inspector=inspector, llm=mock_llm)
    result = gen.generate("What are all the names and countries of singers?")
    assert result.validation is not None
    assert result.generation_time_ms >= 0
