"""Main NL-to-SQL Pipeline — unified interface orchestrating generation, correction, and explanation."""

import time
from pathlib import Path
from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field

from .core.db_engine import DatabaseEngine, ExecutionResult
from .core.schema_inspector import SchemaInspector
from .llm.base import BaseLLMClient
from .llm.mock_client import MockLLMClient
from .llm import get_llm_client
from .config import SystemConfig, default_config

# Defensive imports for core validator
try:
    from .core.validator import SQLValidator, ValidationResult
except ImportError:
    class ValidationResult(BaseModel):  # type: ignore
        is_valid: bool = True
        sql: str = ""
        syntax_error: Optional[str] = None
        schema_errors: List[str] = Field(default_factory=list)
        all_errors: List[str] = Field(default_factory=list)

    class SQLValidator:  # type: ignore
        def __init__(self, inspector=None):
            self.inspector = inspector
        def clean_markdown_fences(self, sql: str) -> str:
            return sql.strip().replace("```sql", "").replace("```", "").strip().rstrip(";")
        def validate(self, sql: str) -> ValidationResult:
            cleaned = self.clean_markdown_fences(sql)
            return ValidationResult(is_valid=bool(cleaned), sql=cleaned)

# Defensive imports for generators
try:
    from .generators.zero_shot import ZeroShotSQLGenerator
    from .generators.few_shot import FewShotSQLGenerator
    from .generators.cot_planner import CoTPlannerSQLGenerator
    from .generators.base import GenerationResult
except ImportError:
    class GenerationResult(BaseModel):  # type: ignore
        strategy: str
        question: str
        generated_sql: str
        raw_response: str = ""
        prompt_used: str = ""
        query_plan: Optional[Any] = None
        validation: Optional[ValidationResult] = None
        generation_time_ms: float = 0.0

    class _MockBaseGen:
        def __init__(self, inspector, llm, validator=None):
            self.inspector = inspector
            self.llm = llm
            self.validator = validator or SQLValidator(inspector)
        def generate(self, question: str) -> GenerationResult:
            resp = self.llm.generate(f"Schema:\n{self.inspector.to_compact_markdown()}\nQuestion: {question}")
            sql = self.validator.clean_markdown_fences(resp.content)
            val = self.validator.validate(sql)
            return GenerationResult(strategy="adapter", question=question, generated_sql=sql, validation=val)

    ZeroShotSQLGenerator = _MockBaseGen  # type: ignore
    FewShotSQLGenerator = _MockBaseGen  # type: ignore
    CoTPlannerSQLGenerator = _MockBaseGen  # type: ignore

# Defensive imports for self-correction chain
try:
    from .correction.self_correction_chain import SelfCorrectionChain, SelfCorrectionResult, CorrectionAttempt
except ImportError:
    class CorrectionAttempt(BaseModel):  # type: ignore
        iteration: int = 1
        sql: str = ""
        validation: Optional[ValidationResult] = None
        execution: Optional[ExecutionResult] = None
        thought: Optional[str] = None
        duration_ms: float = 0.0

    class SelfCorrectionResult(BaseModel):  # type: ignore
        success: bool = True
        question: str = ""
        initial_sql: str = ""
        final_sql: str = ""
        iterations_used: int = 1
        attempts: List[CorrectionAttempt] = Field(default_factory=list)
        final_execution: Optional[ExecutionResult] = None
        total_time_ms: float = 0.0

    class SelfCorrectionChain:  # type: ignore
        def __init__(self, db_engine, inspector, llm, max_iterations=3, validator=None):
            self.db_engine = db_engine
            self.inspector = inspector
            self.llm = llm
            self.max_iterations = max_iterations
            self.validator = validator or SQLValidator(inspector)
        def run(self, question: str, initial_sql: str) -> SelfCorrectionResult:
            exec_res = self.db_engine.execute_query(initial_sql)
            return SelfCorrectionResult(
                success=exec_res.success,
                question=question,
                initial_sql=initial_sql,
                final_sql=initial_sql,
                iterations_used=1,
                final_execution=exec_res,
            )

# Defensive imports for ReAct Agent
try:
    from .agent.react_agent import ReActSQLAgent, AgentRunResult, AgentStep
except ImportError:
    class AgentStep(BaseModel):  # type: ignore
        step_number: int = 1
        thought: str = ""
        action: Optional[str] = None
        action_input: Optional[Dict[str, Any]] = None
        observation: Optional[str] = None
        duration_ms: float = 0.0

    class AgentRunResult(BaseModel):  # type: ignore
        success: bool = True
        question: str = ""
        final_sql: str = ""
        final_answer: str = ""
        steps: List[AgentStep] = Field(default_factory=list)
        tool_calls_count: int = 0
        final_execution: Optional[ExecutionResult] = None
        total_time_ms: float = 0.0

    class ReActSQLAgent:  # type: ignore
        def __init__(self, db_engine, inspector, llm, max_steps=6, validator=None):
            self.db_engine = db_engine
            self.inspector = inspector
            self.llm = llm
        def run(self, question: str) -> AgentRunResult:
            resp = self.llm.generate(f"Solve: {question}")
            sql = resp.content.strip().replace("```sql", "").replace("```", "").strip()
            exec_res = self.db_engine.execute_query(sql)
            return AgentRunResult(
                success=exec_res.success,
                question=question,
                final_sql=sql,
                final_answer=f"Result count: {exec_res.row_count}",
                final_execution=exec_res,
            )

# Defensive imports for Result Explainer
try:
    from .explainer.result_explainer import ExplanationService, QueryAndResultExplanation
except ImportError:
    class QueryAndResultExplanation(BaseModel):  # type: ignore
        query_breakdown: str = ""
        result_summary: str = ""
        key_insights: List[str] = Field(default_factory=list)

    class ExplanationService:  # type: ignore
        def __init__(self, llm):
            self.llm = llm
        def explain(self, question: str, sql: str, result: ExecutionResult) -> QueryAndResultExplanation:
            return QueryAndResultExplanation(
                query_breakdown=f"Executes query: {sql}",
                result_summary=f"Returned {result.row_count} rows.",
                key_insights=[f"Execution time: {result.execution_time_ms}ms"],
            )


StrategyType = Literal["zero_shot", "few_shot", "cot_planner"]


class PipelineResult(BaseModel):
    """Full pipeline execution result for a single question."""
    question: str
    strategy: str
    generated_sql: str
    final_sql: str
    sql: str = ""
    rows: List[List[Any]] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    validation_info: Optional[ValidationResult] = None
    correction_attempts: List[CorrectionAttempt] = Field(default_factory=list)
    agent_trajectory: List[AgentStep] = Field(default_factory=list)
    explanation: Optional[QueryAndResultExplanation] = None
    timings: Dict[str, float] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    execution: Optional[ExecutionResult] = None
    correction: Optional[SelfCorrectionResult] = None
    generation: Optional[GenerationResult] = None
    total_time_ms: float = 0.0

    @property
    def success(self) -> bool:
        return self.execution is not None and self.execution.success


class AgentPipelineResult(BaseModel):
    """Full agent pipeline result for a single question."""
    question: str
    sql: str = ""
    rows: List[List[Any]] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    agent_trajectory: List[AgentStep] = Field(default_factory=list)
    agent_run: Optional[AgentRunResult] = None
    explanation: Optional[QueryAndResultExplanation] = None
    timings: Dict[str, float] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    total_time_ms: float = 0.0

    @property
    def success(self) -> bool:
        return self.agent_run is not None and self.agent_run.success


class NL2SQLPipeline:
    """
    Unified NL-to-SQL Pipeline combining:
    - Schema-aware generation (zero-shot, few-shot, CoT)
    - AST syntax and safety validation
    - Database execution in read-only sandbox mode
    - Self-correction prompt chain on failure
    - Optional ReAct database agent mode
    - Query and tabular result explanation in plain English
    """

    def __init__(
        self,
        db_path: str,
        config: Optional[SystemConfig] = None,
        llm: Optional[BaseLLMClient] = None,
    ):
        self.db_path = str(db_path)
        self.config = config or SystemConfig(provider="mock")
        self.engine = DatabaseEngine(self.db_path, timeout=self.config.query_timeout_seconds)
        self.inspector = SchemaInspector(self.db_path)
        self.validator = SQLValidator(inspector=self.inspector)
        # Default to Mock LLM if no specific provider/client is passed
        if llm is not None:
            self.llm = llm
        elif config is not None:
            self.llm = get_llm_client(self.config)
        else:
            self.llm = MockLLMClient()
        self.explainer = ExplanationService(llm=self.llm)

    def _get_generator(self, strategy: StrategyType):
        if strategy == "zero_shot":
            return ZeroShotSQLGenerator(inspector=self.inspector, llm=self.llm, validator=self.validator)
        elif strategy == "few_shot":
            return FewShotSQLGenerator(inspector=self.inspector, llm=self.llm, validator=self.validator)
        elif strategy == "cot_planner":
            return CoTPlannerSQLGenerator(inspector=self.inspector, llm=self.llm, validator=self.validator)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def run(
        self,
        question: str,
        strategy: StrategyType = "cot_planner",
        use_self_correction: bool = True,
        explain_results: bool = True,
    ) -> PipelineResult:
        """
        Run the full NL-to-SQL pipeline for a single natural language question.
        
        Args:
            question: The natural language question.
            strategy: SQL generation strategy (zero_shot, few_shot, cot_planner).
            use_self_correction: If True, attempt to fix execution errors iteratively.
            explain_results: If True, generate a natural language explanation.
        """
        t_start = time.perf_counter()
        errors: List[str] = []

        # 1. Generate initial SQL
        generator = self._get_generator(strategy)
        gen_result = generator.generate(question)
        initial_sql = gen_result.generated_sql
        val_result = gen_result.validation

        correction_result: Optional[SelfCorrectionResult] = None
        final_sql = initial_sql
        final_exec: Optional[ExecutionResult] = None

        # Check for upfront validation errors
        if val_result and not val_result.is_valid:
            errors.extend(val_result.all_errors)

        # 2. Self-correction chain or direct execution
        if use_self_correction:
            chain = SelfCorrectionChain(
                db_engine=self.engine,
                inspector=self.inspector,
                llm=self.llm,
                max_iterations=self.config.max_correction_iterations,
                validator=self.validator,
            )
            correction_result = chain.run(question, initial_sql=initial_sql)
            final_sql = correction_result.final_sql
            final_exec = correction_result.final_execution
        else:
            clean_sql = self.validator.clean_markdown_fences(initial_sql)
            final_exec = self.engine.execute_query(clean_sql)
            final_sql = clean_sql

        if final_exec and not final_exec.success and final_exec.error_message:
            errors.append(final_exec.error_message)

        # 3. Natural language explanation
        explanation: Optional[QueryAndResultExplanation] = None
        if explain_results and final_exec is not None:
            explanation = self.explainer.explain(
                question=question,
                sql=final_sql,
                result=final_exec,
            )

        total_ms = (time.perf_counter() - t_start) * 1000.0
        timings = {
            "total_time_ms": round(total_ms, 2),
            "generation_time_ms": round(gen_result.generation_time_ms, 2),
            "execution_time_ms": round(final_exec.execution_time_ms, 2) if final_exec else 0.0,
        }

        return PipelineResult(
            question=question,
            strategy=strategy,
            generated_sql=initial_sql,
            final_sql=final_sql,
            sql=final_sql,
            rows=final_exec.rows if final_exec else [],
            columns=final_exec.columns if final_exec else [],
            validation_info=val_result,
            correction_attempts=correction_result.attempts if correction_result else [],
            agent_trajectory=[],
            explanation=explanation,
            timings=timings,
            errors=errors,
            execution=final_exec,
            correction=correction_result,
            generation=gen_result,
            total_time_ms=round(total_ms, 2),
        )

    def run_agent(self, question: str, explain_results: bool = True) -> AgentPipelineResult:
        """Run the ReAct SQL Agent pipeline with database tools."""
        t_start = time.perf_counter()
        errors: List[str] = []

        agent = ReActSQLAgent(
            db_engine=self.engine,
            inspector=self.inspector,
            llm=self.llm,
            max_steps=6,
            validator=self.validator,
        )
        agent_result = agent.run(question)

        if not agent_result.success:
            if agent_result.final_execution and agent_result.final_execution.error_message:
                errors.append(agent_result.final_execution.error_message)
            else:
                errors.append("Agent failed to reach a successful execution.")

        explanation = None
        if explain_results and agent_result.final_execution is not None:
            explanation = self.explainer.explain(
                question=question,
                sql=agent_result.final_sql,
                result=agent_result.final_execution,
            )

        total_ms = (time.perf_counter() - t_start) * 1000.0
        timings = {
            "total_time_ms": round(total_ms, 2),
            "agent_time_ms": round(agent_result.total_time_ms, 2),
        }

        return AgentPipelineResult(
            question=question,
            sql=agent_result.final_sql,
            rows=agent_result.final_execution.rows if agent_result.final_execution else [],
            columns=agent_result.final_execution.columns if agent_result.final_execution else [],
            agent_trajectory=agent_result.steps,
            agent_run=agent_result,
            explanation=explanation,
            timings=timings,
            errors=errors,
            total_time_ms=round(total_ms, 2),
        )
