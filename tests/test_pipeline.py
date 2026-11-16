"""Integration tests for the complete NL2SQL pipeline."""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nl2sql.pipeline import NL2SQLPipeline
from nl2sql.config import SystemConfig
from nl2sql.llm.mock_client import MockLLMClient


DB_PATH = Path(__file__).parent.parent / "data" / "benchmark_100" / "databases" / "concert_singer.sqlite"


@pytest.fixture
def mock_pipeline():
    if not DB_PATH.exists():
        pytest.skip("Benchmark DB not found. Run setup_benchmark.py first.")
    cfg = SystemConfig(provider="mock")
    mock_llm = MockLLMClient()
    mock_llm.register_gold_queries({
        "how many singers do we have?": "SELECT count(*) FROM singer",
        "list all singer names": "SELECT Name FROM singer",
        "what is the average age of all singers?": "SELECT avg(Age) FROM singer",
        "find singer names who did not participate in any concert.": "SELECT Name FROM singer WHERE Singer_ID NOT IN (SELECT Singer_ID FROM singer_in_concert)",
    })
    return NL2SQLPipeline(db_path=str(DB_PATH), config=cfg, llm=mock_llm)


def test_pipeline_zero_shot_success(mock_pipeline):
    """Test standard successful generation via zero-shot strategy."""
    result = mock_pipeline.run(
        "How many singers do we have?",
        strategy="zero_shot",
        use_self_correction=False,
        explain_results=False,
    )
    assert result.strategy == "zero_shot"
    assert result.generated_sql != ""
    assert result.sql == result.final_sql
    assert result.success is True
    assert len(result.rows) > 0


def test_pipeline_cot_planner(mock_pipeline):
    """Test Chain-of-Thought planner generation strategy."""
    result = mock_pipeline.run(
        "What is the average age of all singers?",
        strategy="cot_planner",
        use_self_correction=False,
        explain_results=False,
    )
    assert result.strategy == "cot_planner"
    assert result.generation is not None
    assert result.generation.query_plan is not None
    assert result.success is True


def test_pipeline_self_correction_enabled(mock_pipeline):
    """Test self-correction path when correction is enabled."""
    result = mock_pipeline.run(
        "How many singers do we have?",
        strategy="zero_shot",
        use_self_correction=True,
        explain_results=False,
    )
    assert result.correction is not None
    assert result.success is True
    assert isinstance(result.correction_attempts, list)


def test_pipeline_validation_failure(mock_pipeline):
    """Test validation failure path for destructive statements."""
    # When validator catches a disallowed statement, error is captured
    val = mock_pipeline.validator.validate("DROP TABLE singer;")
    assert not val.is_valid
    assert not val.is_read_only

    # Pipeline direct execution of disallowed query is captured
    res = mock_pipeline.engine.execute_query("DROP TABLE singer;")
    assert not res.success
    assert res.error_type == "DISALLOWED_OPERATION"


def test_pipeline_explanation_generated(mock_pipeline):
    """Test natural language explanation generation."""
    result = mock_pipeline.run(
        "How many singers do we have?",
        strategy="zero_shot",
        use_self_correction=True,
        explain_results=True,
    )
    if result.success:
        assert result.explanation is not None
        assert result.explanation.result_summary != ""


def test_pipeline_agent_run(mock_pipeline):
    """Test ReAct agent execution mode."""
    agent_result = mock_pipeline.run_agent(
        "How many singers do we have?",
        explain_results=False,
    )
    assert agent_result.agent_run is not None
    assert agent_result.total_time_ms >= 0
    assert isinstance(agent_result.agent_trajectory, list)


def test_pipeline_with_nonexistent_question(mock_pipeline):
    """Pipeline should not crash on unknown questions — returns a best-effort result."""
    result = mock_pipeline.run(
        "What is the weather today?",
        strategy="zero_shot",
        use_self_correction=False,
        explain_results=False,
    )
    assert result.generated_sql is not None


def test_schema_accessible_from_pipeline(mock_pipeline):
    """Test schema inspector integration in pipeline."""
    tables = mock_pipeline.inspector.get_table_names()
    assert "singer" in tables
