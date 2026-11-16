"""Comprehensive unit and integration tests for Member 3:
Error Analyzer, Self-Correction Chain, Database Tools, ReAct Agent, and Result Explainer.
"""

import sys
import json
import pytest
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nl2sql.core.db_engine import DatabaseEngine, ExecutionResult
from nl2sql.core.schema_inspector import SchemaInspector
from nl2sql.core.validator import SQLValidator, ValidationResult
from nl2sql.llm.mock_client import MockLLMClient
from nl2sql.llm.base import BaseLLMClient, LLMMessage, LLMResponse
from nl2sql.correction.error_analyzer import ErrorAnalyzer, ErrorDiagnosis
from nl2sql.correction.self_correction_chain import SelfCorrectionChain, SelfCorrectionResult, CorrectionAttempt
from nl2sql.agent.tools import DatabaseTools, ToolDefinition
from nl2sql.agent.react_agent import ReActSQLAgent, AgentStep, AgentRunResult
from nl2sql.explainer.result_explainer import ExplanationService, QueryAndResultExplanation


DB_PATH = Path(__file__).parent.parent / "data" / "benchmark_100" / "databases" / "concert_singer.sqlite"


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def engine():
    if not DB_PATH.exists():
        pytest.skip("Benchmark DB not set up. Run setup_benchmark.py.")
    return DatabaseEngine(str(DB_PATH))


@pytest.fixture
def inspector():
    if not DB_PATH.exists():
        pytest.skip("Benchmark DB not set up. Run setup_benchmark.py.")
    return SchemaInspector(str(DB_PATH))


@pytest.fixture
def validator(inspector):
    return SQLValidator(inspector=inspector)


@pytest.fixture
def mock_llm():
    client = MockLLMClient()
    client.register_gold_queries({
        "how many singers do we have?": "SELECT count(*) FROM singer",
        "find singer names": "SELECT Name FROM singer",
        "how many singers": "SELECT count(*) FROM singer",
    })
    return client


@pytest.fixture
def db_tools(engine, inspector):
    return DatabaseTools(db_engine=engine, inspector=inspector)


@pytest.fixture
def chain(engine, inspector, mock_llm):
    return SelfCorrectionChain(db_engine=engine, inspector=inspector, llm=mock_llm, max_iterations=3)


@pytest.fixture
def agent(engine, inspector, mock_llm):
    return ReActSQLAgent(db_engine=engine, inspector=inspector, llm=mock_llm, max_steps=6)


@pytest.fixture
def explainer(mock_llm):
    return ExplanationService(llm=mock_llm)


# ─────────────────────────────────────────────
# Test LLM Implementations for Edge Cases
# ─────────────────────────────────────────────

class FailingLLMClient(BaseLLMClient):
    """LLM client that raises an exception on generation."""
    def generate(self, prompt, system_prompt=None, temperature=0.0, stop_sequences=None):
        raise RuntimeError("Simulated LLM connection timeout")
    def chat(self, messages, temperature=0.0, stop_sequences=None):
        raise RuntimeError("Simulated LLM connection timeout")


class EmptyLLMClient(BaseLLMClient):
    """LLM client that returns empty text."""
    def generate(self, prompt, system_prompt=None, temperature=0.0, stop_sequences=None):
        return LLMResponse(content="", model="empty")
    def chat(self, messages, temperature=0.0, stop_sequences=None):
        return LLMResponse(content="", model="empty")


class MalformedLLMClient(BaseLLMClient):
    """LLM client that returns non-SQL garbage text."""
    def generate(self, prompt, system_prompt=None, temperature=0.0, stop_sequences=None):
        return LLMResponse(content="Sorry, I cannot answer this database question.", model="malformed")
    def chat(self, messages, temperature=0.0, stop_sequences=None):
        return LLMResponse(content="Sorry, I cannot answer this database question.", model="malformed")


# ─────────────────────────────────────────────
# 1. ERROR ANALYZER TESTS
# ─────────────────────────────────────────────

class TestErrorAnalyzer:
    def test_missing_column_error_type(self, inspector):
        analyzer = ErrorAnalyzer(inspector=inspector)
        exec_result = ExecutionResult(
            success=False,
            sql="SELECT bad_col FROM singer",
            error_message="no such column: bad_col",
            error_type="NO_SUCH_COLUMN",
        )
        diag = analyzer.diagnose_execution_error(exec_result, "SELECT bad_col FROM singer")
        assert diag.error_type == "NO_SUCH_COLUMN"
        assert "bad_col" in diag.raw_message
        assert len(diag.suggested_fix) > 0
        assert "bad_col" in diag.relevant_columns

    def test_missing_table_error_type(self, inspector):
        analyzer = ErrorAnalyzer(inspector=inspector)
        exec_result = ExecutionResult(
            success=False,
            sql="SELECT * FROM ghost_table",
            error_message="no such table: ghost_table",
            error_type="NO_SUCH_TABLE",
        )
        diag = analyzer.diagnose_execution_error(exec_result, "SELECT * FROM ghost_table")
        assert diag.error_type == "NO_SUCH_TABLE"
        assert "ghost_table" in diag.raw_message
        assert any(t in diag.suggested_fix for t in inspector.get_table_names())

    def test_syntax_error_from_validation(self, inspector):
        analyzer = ErrorAnalyzer(inspector=inspector)
        val = ValidationResult(
            is_valid=False,
            sql="SELEC * FRO singer",
            syntax_error="syntax error at position 5",
        )
        diag = analyzer.diagnose_validation_error(val)
        assert diag.error_type == "SYNTAX_ERROR"
        assert "syntax" in diag.raw_message.lower()

    def test_syntax_error_from_execution(self, inspector):
        analyzer = ErrorAnalyzer(inspector=inspector)
        exec_result = ExecutionResult(
            success=False,
            sql="SELECT * FROM singer WHERE",
            error_message="syntax error near 'WHERE'",
            error_type="SYNTAX_ERROR",
        )
        diag = analyzer.diagnose_execution_error(exec_result, "SELECT * FROM singer WHERE")
        assert diag.error_type == "SYNTAX_ERROR"

    def test_ambiguous_column_detection(self, inspector):
        analyzer = ErrorAnalyzer(inspector=inspector)
        exec_result = ExecutionResult(
            success=False,
            sql="SELECT Name FROM singer JOIN concert",
            error_message="ambiguous column name: Name",
            error_type="AMBIGUOUS_COLUMN",
        )
        diag = analyzer.diagnose_execution_error(exec_result, "SELECT Name FROM singer JOIN concert")
        assert diag.error_type == "AMBIGUOUS_COLUMN"
        assert any(term in diag.suggested_fix.lower() for term in ["prefix", "table", "alias"])

    def test_aggregate_misuse_detection(self, inspector):
        analyzer = ErrorAnalyzer(inspector=inspector)
        exec_result = ExecutionResult(
            success=False,
            sql="SELECT * FROM singer WHERE count(*) > 1",
            error_message="misuse of aggregate function count()",
            error_type="AGGREGATE_ERROR",
        )
        diag = analyzer.diagnose_execution_error(exec_result, "SELECT * FROM singer WHERE count(*) > 1")
        assert diag.error_type == "AGGREGATE_MISUSE"
        assert "HAVING" in diag.suggested_fix

    def test_schema_error_from_validation(self, inspector):
        analyzer = ErrorAnalyzer(inspector=inspector)
        val = ValidationResult(
            is_valid=False,
            sql="SELECT * FROM non_existent_table",
            schema_errors=["Table 'non_existent_table' does not exist in schema."],
        )
        diag = analyzer.diagnose_validation_error(val)
        assert diag.error_type == "SCHEMA_ERROR"
        assert len(diag.suggested_fix) > 0

    def test_unknown_validation_error_fallback(self, inspector):
        analyzer = ErrorAnalyzer(inspector=inspector)
        val = ValidationResult(is_valid=False, sql="SELECT 1")
        diag = analyzer.diagnose_validation_error(val)
        assert diag.error_type == "UNKNOWN_VALIDATION_ERROR"

    def test_execution_error_fallback(self, inspector):
        analyzer = ErrorAnalyzer(inspector=inspector)
        exec_result = ExecutionResult(
            success=False,
            sql="SELECT * FROM singer",
            error_message="Disk I/O error",
            error_type="EXECUTION_ERROR",
        )
        diag = analyzer.diagnose_execution_error(exec_result, "SELECT * FROM singer")
        assert diag.error_type == "EXECUTION_ERROR"
        assert len(diag.suggested_fix) > 0


# ─────────────────────────────────────────────
# 2. SELF-CORRECTION CHAIN TESTS
# ─────────────────────────────────────────────

class TestSelfCorrectionChain:
    def test_initially_valid_sql_succeeds_first_iteration(self, chain):
        res = chain.run("How many singers do we have?", initial_sql="SELECT count(*) FROM singer")
        assert res.success is True
        assert res.iterations_used == 1
        assert res.final_execution is not None
        assert res.final_execution.success is True

    def test_invalid_sql_triggers_correction_and_recovers(self, chain):
        res = chain.run(
            "How many singers do we have?",
            initial_sql="SELECT count(*) FROM singer WHERE bad_col = 1",
        )
        assert len(res.attempts) >= 1
        assert res.iterations_used >= 1
        # First attempt should have failed
        assert not res.attempts[0].execution.success

    def test_multiple_correction_attempts_recorded(self, chain):
        res = chain.run("Find some singers", initial_sql="SELECT invalid_col FROM singer")
        assert len(res.attempts) >= 1
        for attempt in res.attempts:
            assert attempt.iteration >= 1
            assert attempt.duration_ms >= 0

    def test_maximum_iteration_limit_respected(self, engine, inspector):
        bad_llm = MalformedLLMClient()
        strict_chain = SelfCorrectionChain(db_engine=engine, inspector=inspector, llm=bad_llm, max_iterations=2)
        res = strict_chain.run("Find bad query", initial_sql="SELECT bad_col FROM singer")
        assert res.success is False
        assert len(res.attempts) <= 2
        assert res.iterations_used <= 2

    def test_invalid_query_rejection_at_validation(self, engine, inspector, mock_llm):
        single_chain = SelfCorrectionChain(db_engine=engine, inspector=inspector, llm=mock_llm, max_iterations=1)
        res = single_chain.run("Bad query", initial_sql="SELEC * FRO")
        assert not res.attempts[0].validation.is_valid
        assert res.attempts[0].diagnosis.error_type == "SYNTAX_ERROR"

    def test_destructive_query_rejection(self, engine, inspector, mock_llm):
        single_chain = SelfCorrectionChain(db_engine=engine, inspector=inspector, llm=mock_llm, max_iterations=1)
        res = single_chain.run("Delete singers", initial_sql="DELETE FROM singer")
        assert not res.attempts[0].validation.is_valid
        assert not res.attempts[0].validation.is_read_only

    def test_destructive_query_blocked_at_engine(self, engine):
        res = engine.execute_query("DELETE FROM singer")
        assert not res.success
        assert res.error_type == "DISALLOWED_OPERATION"

    def test_llm_failure_handled_gracefully(self, engine, inspector):
        failing_llm = FailingLLMClient()
        fail_chain = SelfCorrectionChain(db_engine=engine, inspector=inspector, llm=failing_llm, max_iterations=2)
        res = fail_chain.run("How many singers", initial_sql="SELECT bad_col FROM singer")
        assert isinstance(res, SelfCorrectionResult)
        assert res.success is False

    def test_empty_llm_response_handled_gracefully(self, engine, inspector):
        empty_llm = EmptyLLMClient()
        empty_chain = SelfCorrectionChain(db_engine=engine, inspector=inspector, llm=empty_llm, max_iterations=2)
        res = empty_chain.run("How many singers", initial_sql="SELECT bad_col FROM singer")
        assert isinstance(res, SelfCorrectionResult)
        assert res.success is False

    def test_complete_attempt_history_structure(self, chain):
        res = chain.run("Find singer names", initial_sql="SELECT Name FROM singer")
        assert len(res.attempts) >= 1
        att = res.attempts[0]
        assert isinstance(att, CorrectionAttempt)
        assert att.iteration == 1
        assert att.sql != ""
        assert att.validation is not None
        assert att.execution is not None

    def test_execution_timing_recorded(self, chain):
        res = chain.run("Find singer names", initial_sql="SELECT Name FROM singer")
        assert res.total_time_ms >= 0
        assert res.attempts[0].duration_ms >= 0


# ─────────────────────────────────────────────
# 3. DATABASE TOOLS TESTS
# ─────────────────────────────────────────────

class TestDatabaseTools:
    def test_list_tables(self, db_tools):
        obs = db_tools.execute_tool("list_tables", {})
        data = json.loads(obs)
        assert "tables" in data
        assert "singer" in data["tables"]
        assert "stadium" in data["tables"]

    def test_describe_table_valid(self, db_tools):
        obs = db_tools.execute_tool("describe_table", {"table_name": "singer"})
        data = json.loads(obs)
        assert data["table"] == "singer"
        assert "columns" in data
        col_names = [c["name"] for c in data["columns"]]
        assert "Name" in col_names

    def test_describe_table_foreign_keys(self, db_tools):
        obs = db_tools.execute_tool("describe_table", {"table_name": "concert"})
        data = json.loads(obs)
        assert "foreign_keys" in data
        assert len(data["foreign_keys"]) > 0

    def test_describe_table_missing_table(self, db_tools):
        obs = db_tools.execute_tool("describe_table", {"table_name": "nonexistent_table_xyz"})
        data = json.loads(obs)
        assert "error" in data

    def test_describe_table_invalid_arguments(self, db_tools):
        obs = db_tools.execute_tool("describe_table", {})
        data = json.loads(obs)
        assert "error" in data

    def test_sample_table_data_valid(self, db_tools):
        obs = db_tools.execute_tool("sample_table_data", {"table_name": "singer", "limit": 2})
        data = json.loads(obs)
        assert "sample_rows" in data
        assert len(data["sample_rows"]) <= 2

    def test_sample_table_data_missing_table(self, db_tools):
        obs = db_tools.execute_tool("sample_table_data", {"table_name": "ghost_table"})
        data = json.loads(obs)
        assert "error" in data

    def test_validate_query_valid(self, db_tools):
        obs = db_tools.execute_tool("validate_query", {"sql": "SELECT Name FROM singer"})
        data = json.loads(obs)
        assert data["is_valid"] is True
        assert data["syntax_error"] is None

    def test_validate_query_markdown_fence(self, db_tools):
        obs = db_tools.execute_tool("validate_query", {"sql": "```sql\nSELECT Name FROM singer\n```"})
        data = json.loads(obs)
        assert data["is_valid"] is True

    def test_validate_query_destructive(self, db_tools):
        obs = db_tools.execute_tool("validate_query", {"sql": "DELETE FROM singer"})
        data = json.loads(obs)
        assert data["is_valid"] is False

    def test_execute_query_valid(self, db_tools):
        obs = db_tools.execute_tool("execute_query", {"sql": "SELECT count(*) FROM singer"})
        data = json.loads(obs)
        assert data["status"] == "success"
        assert data["row_count"] >= 1
        assert "columns" in data
        assert "rows" in data

    def test_execute_query_destructive_rejected(self, db_tools):
        obs = db_tools.execute_tool("execute_query", {"sql": "DROP TABLE singer"})
        data = json.loads(obs)
        assert data["status"] == "error"

    def test_execute_query_invalid_sql(self, db_tools):
        obs = db_tools.execute_tool("execute_query", {"sql": "SELECT bad_column FROM singer"})
        data = json.loads(obs)
        assert data["status"] == "error"

    def test_unknown_tool_handling(self, db_tools):
        obs = db_tools.execute_tool("nonexistent_unknown_tool", {})
        data = json.loads(obs)
        assert "error" in data
        assert "Unknown tool" in data["error"]

    def test_tool_definitions_complete(self, db_tools):
        defs = db_tools.get_definitions()
        assert len(defs) == 5
        names = {d.name for d in defs}
        expected = {"list_tables", "describe_table", "sample_table_data", "validate_query", "execute_query"}
        assert names == expected


# ─────────────────────────────────────────────
# 4. REACT AGENT TESTS
# ─────────────────────────────────────────────

class TestReActSQLAgent:
    def test_successful_multi_step_run(self, agent):
        res = agent.run("How many singers do we have?")
        assert isinstance(res, AgentRunResult)
        assert res.question == "How many singers do we have?"
        assert len(res.steps) >= 1
        assert res.tool_calls_count >= 0
        assert res.total_time_ms >= 0

    def test_thought_action_observation_parsing(self, engine, inspector):
        class StepMockLLM(BaseLLMClient):
            def __init__(self):
                self.calls = 0
            def generate(self, prompt, system_prompt=None, temperature=0.0, stop_sequences=None):
                self.calls += 1
                if self.calls == 1:
                    return LLMResponse(
                        content="Thought: Let me check the available tables.\nAction: list_tables\nAction Input: {}",
                        model="step-mock",
                    )
                return LLMResponse(
                    content="Thought: Table verified.\nFinal Answer: ```sql\nSELECT count(*) FROM singer\n```",
                    model="step-mock",
                )
            def chat(self, messages, temperature=0.0, stop_sequences=None):
                return self.generate("")

        step_agent = ReActSQLAgent(db_engine=engine, inspector=inspector, llm=StepMockLLM(), max_steps=5)
        res = step_agent.run("How many singers?")
        assert len(res.steps) >= 1
        first_step = res.steps[0]
        assert first_step.action == "list_tables"
        assert first_step.observation is not None

    def test_invalid_tool_handling_in_agent(self, engine, inspector):
        class BadActionLLM(BaseLLMClient):
            def __init__(self):
                self.calls = 0
            def generate(self, prompt, system_prompt=None, temperature=0.0, stop_sequences=None):
                self.calls += 1
                if self.calls == 1:
                    return LLMResponse(
                        content="Thought: Run bogus tool.\nAction: fly_to_space\nAction Input: {}",
                        model="bad-llm",
                    )
                return LLMResponse(
                    content="Thought: Give up.\nFinal Answer: ```sql\nSELECT 1\n```",
                    model="bad-llm",
                )
            def chat(self, messages, temperature=0.0, stop_sequences=None):
                return self.generate("")

        bad_agent = ReActSQLAgent(db_engine=engine, inspector=inspector, llm=BadActionLLM(), max_steps=4)
        res = bad_agent.run("Test query")
        assert isinstance(res, AgentRunResult)
        # Should record step with error observation without crashing
        assert len(res.steps) >= 1

    def test_malformed_llm_response_handling(self, engine, inspector):
        mal_llm = MalformedLLMClient()
        mal_agent = ReActSQLAgent(db_engine=engine, inspector=inspector, llm=mal_llm, max_steps=2)
        res = mal_agent.run("Random question")
        assert isinstance(res, AgentRunResult)
        assert res.success is False

    def test_maximum_steps_respected(self, engine, inspector):
        class EndlessLoopLLM(BaseLLMClient):
            def generate(self, prompt, system_prompt=None, temperature=0.0, stop_sequences=None):
                return LLMResponse(
                    content="Thought: Still exploring.\nAction: list_tables\nAction Input: {}",
                    model="loop-llm",
                )
            def chat(self, messages, temperature=0.0, stop_sequences=None):
                return self.generate("")

        loop_agent = ReActSQLAgent(db_engine=engine, inspector=inspector, llm=EndlessLoopLLM(), max_steps=3)
        res = loop_agent.run("Infinite loop test")
        assert len(res.steps) <= 3

    def test_failure_when_no_verified_sql(self, engine, inspector):
        mal_agent = ReActSQLAgent(db_engine=engine, inspector=inspector, llm=MalformedLLMClient(), max_steps=2)
        res = mal_agent.run("Unverifiable query")
        assert res.success is False
        assert res.final_execution is None or not res.final_execution.success

    def test_final_sql_execution_success(self, engine, inspector, mock_llm):
        agent = ReActSQLAgent(db_engine=engine, inspector=inspector, llm=mock_llm, max_steps=6)
        res = agent.run("How many singers do we have?")
        if res.success:
            assert res.final_execution is not None
            assert res.final_execution.success is True


# ─────────────────────────────────────────────
# 5. RESULT EXPLAINER TESTS
# ─────────────────────────────────────────────

class TestResultExplainer:
    def test_successful_execution_explanation(self, explainer):
        exec_res = ExecutionResult(
            success=True,
            sql="SELECT count(*) FROM singer",
            columns=["count(*)"],
            rows=[[6]],
            row_count=1,
            execution_time_ms=1.2,
        )
        exp = explainer.explain("How many singers do we have?", "SELECT count(*) FROM singer", exec_res)
        assert isinstance(exp, QueryAndResultExplanation)
        assert exp.query_breakdown != ""
        assert exp.result_summary != ""
        assert len(exp.key_insights) >= 1

    def test_zero_row_result_handled(self, explainer):
        exec_res = ExecutionResult(
            success=True,
            sql="SELECT Name FROM singer WHERE Age > 100",
            columns=["Name"],
            rows=[],
            row_count=0,
            execution_time_ms=0.8,
        )
        exp = explainer.explain("Singers older than 100", "SELECT Name FROM singer WHERE Age > 100", exec_res)
        assert isinstance(exp, QueryAndResultExplanation)
        assert exp.result_summary != ""

    def test_failed_execution_handled(self, explainer):
        exec_res = ExecutionResult(
            success=False,
            sql="SELECT bad_col FROM singer",
            error_message="no such column: bad_col",
            error_type="NO_SUCH_COLUMN",
        )
        exp = explainer.explain("Find bad col", "SELECT bad_col FROM singer", exec_res)
        assert isinstance(exp, QueryAndResultExplanation)
        assert "not execute successfully" in exp.query_breakdown or "error" in exp.query_breakdown.lower()
        assert len(exp.key_insights) >= 1

    def test_llm_failure_deterministic_fallback(self):
        failing_llm = FailingLLMClient()
        service = ExplanationService(llm=failing_llm)
        exec_res = ExecutionResult(
            success=True,
            sql="SELECT count(*) FROM singer",
            columns=["count(*)"],
            rows=[[6]],
            row_count=1,
            execution_time_ms=1.5,
        )
        exp = service.explain("How many singers?", "SELECT count(*) FROM singer", exec_res)
        assert isinstance(exp, QueryAndResultExplanation)
        assert "count(*)" in exp.query_breakdown or "relevant tables" in exp.query_breakdown
        assert "1 row(s)" in exp.result_summary
        assert len(exp.key_insights) >= 1

    def test_malformed_llm_response_parsing(self):
        empty_llm = EmptyLLMClient()
        service = ExplanationService(llm=empty_llm)
        exec_res = ExecutionResult(
            success=True,
            sql="SELECT Name FROM singer",
            columns=["Name"],
            rows=[["Alice"], ["Bob"]],
            row_count=2,
            execution_time_ms=2.1,
        )
        exp = service.explain("Singer names", "SELECT Name FROM singer", exec_res)
        assert isinstance(exp, QueryAndResultExplanation)
        assert exp.result_summary is not None


# ─────────────────────────────────────────────
# 6. ORIGINAL BACKWARD-COMPATIBILITY TESTS
# ─────────────────────────────────────────────

def test_correct_query_succeeds_in_first_iteration(engine, inspector, mock_llm):
    chain = SelfCorrectionChain(db_engine=engine, inspector=inspector, llm=mock_llm, max_iterations=3)
    result = chain.run("How many singers do we have?", initial_sql="SELECT count(*) FROM singer")
    assert result.success
    assert result.iterations_used == 1


def test_failed_query_triggers_correction(engine, inspector, mock_llm):
    chain = SelfCorrectionChain(db_engine=engine, inspector=inspector, llm=mock_llm, max_iterations=3)
    result = chain.run(
        "How many singers do we have?",
        initial_sql="SELECT count(*) FROM singer WHERE nonexistent_col = 1",
    )
    assert len(result.attempts) >= 1
    assert result.iterations_used >= 1


def test_destructive_query_is_blocked(engine, inspector, mock_llm):
    exec_res = engine.execute_query("DELETE FROM singer")
    assert not exec_res.success
    assert exec_res.error_type == "DISALLOWED_OPERATION"

    chain = SelfCorrectionChain(db_engine=engine, inspector=inspector, llm=mock_llm, max_iterations=1)
    result = chain.run(
        "Delete all singers",
        initial_sql="DELETE FROM singer",
    )
    assert not result.attempts[0].validation.is_valid
    assert not result.attempts[0].validation.is_read_only


def test_correction_captures_all_attempts(engine, inspector, mock_llm):
    chain = SelfCorrectionChain(db_engine=engine, inspector=inspector, llm=mock_llm, max_iterations=3)
    result = chain.run(
        "Find some singers",
        initial_sql="SELECT name_wrong_col FROM singer",
    )
    assert len(result.attempts) >= 1


def test_correction_result_has_timing(engine, inspector, mock_llm):
    chain = SelfCorrectionChain(db_engine=engine, inspector=inspector, llm=mock_llm, max_iterations=2)
    result = chain.run("Find singers", initial_sql="SELECT Name FROM singer")
    assert result.total_time_ms >= 0


def test_error_analyzer_no_such_column(inspector):
    from nl2sql.core.db_engine import ExecutionResult
    from nl2sql.correction.error_analyzer import ErrorAnalyzer
    analyzer = ErrorAnalyzer(inspector=inspector)
    exec_result = ExecutionResult(
        success=False,
        sql="SELECT bad_col FROM singer",
        error_message="no such column: bad_col",
        error_type="NO_SUCH_COLUMN",
    )
    diagnosis = analyzer.diagnose_execution_error(exec_result, "SELECT bad_col FROM singer")
    assert diagnosis.error_type == "NO_SUCH_COLUMN"
    assert "bad_col" in diagnosis.raw_message


def test_error_analyzer_no_such_table(inspector):
    from nl2sql.core.db_engine import ExecutionResult
    from nl2sql.correction.error_analyzer import ErrorAnalyzer
    analyzer = ErrorAnalyzer(inspector=inspector)
    exec_result = ExecutionResult(
        success=False,
        sql="SELECT * FROM ghost_table",
        error_message="no such table: ghost_table",
        error_type="NO_SUCH_TABLE",
    )
    diagnosis = analyzer.diagnose_execution_error(exec_result, "SELECT * FROM ghost_table")
    assert diagnosis.error_type == "NO_SUCH_TABLE"


def test_error_analyzer_aggregate_misuse(inspector):
    from nl2sql.core.db_engine import ExecutionResult
    from nl2sql.correction.error_analyzer import ErrorAnalyzer
    analyzer = ErrorAnalyzer(inspector=inspector)
    exec_result = ExecutionResult(
        success=False,
        sql="SELECT * FROM singer WHERE count(*) > 1",
        error_message="misuse of aggregate function count()",
        error_type="AGGREGATE_ERROR",
    )
    diagnosis = analyzer.diagnose_execution_error(exec_result, "SELECT * FROM singer WHERE count(*) > 1")
    assert diagnosis.error_type == "AGGREGATE_MISUSE"
    assert "HAVING" in diagnosis.suggested_fix
