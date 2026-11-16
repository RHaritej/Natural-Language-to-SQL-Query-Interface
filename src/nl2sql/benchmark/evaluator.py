"""Benchmark Evaluator running evaluation on 100-question Spider benchmark subset."""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, Field

from ..core.db_engine import DatabaseEngine, ExecutionResult
from ..core.schema_inspector import SchemaInspector
from ..llm.base import BaseLLMClient
from ..llm.mock_client import MockLLMClient
from .metrics import calculate_exact_match, calculate_execution_accuracy

# Defensive imports for other members' subsystems
try:
    from ..generators.zero_shot import ZeroShotSQLGenerator
    from ..generators.few_shot import FewShotSQLGenerator
    from ..generators.cot_planner import CoTPlannerSQLGenerator
except ImportError:
    ZeroShotSQLGenerator = None  # type: ignore
    FewShotSQLGenerator = None  # type: ignore
    CoTPlannerSQLGenerator = None  # type: ignore

try:
    from ..correction.self_correction_chain import SelfCorrectionChain
except ImportError:
    SelfCorrectionChain = None  # type: ignore

try:
    from ..agent.react_agent import ReActSQLAgent
except ImportError:
    ReActSQLAgent = None  # type: ignore


class BenchmarkQuestion(BaseModel):
    id: int
    db_id: str
    question: str
    gold_sql: str
    difficulty: str = "medium"  # easy, medium, hard, extra-hard


class EvaluationItemResult(BaseModel):
    question_id: int
    db_id: str
    question: str
    difficulty: str
    strategy: str
    pred_sql: str
    gold_sql: str
    exact_match: bool
    execution_accuracy: bool
    iterations: int = 1
    latency_ms: float = 0.0
    error_message: Optional[str] = None


class StrategySummary(BaseModel):
    strategy: str
    total_questions: int
    exact_match_count: int
    execution_match_count: int
    exact_match_accuracy_pct: float
    execution_accuracy_pct: float
    avg_correction_iterations: float
    avg_latency_ms: float
    difficulty_breakdown: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    database_breakdown: Dict[str, Dict[str, float]] = Field(default_factory=dict)


class BenchmarkEvaluator:
    """Evaluates SQL generators, self-correction, and agents on the 100-question benchmark."""

    def __init__(
        self,
        questions_path: Path,
        databases_dir: Path,
        llm: Optional[BaseLLMClient] = None,
    ):
        self.questions_path = Path(questions_path)
        self.databases_dir = Path(databases_dir)
        self.llm = llm or MockLLMClient()
        self.questions: List[BenchmarkQuestion] = self._load_questions()
        self._engines: Dict[str, DatabaseEngine] = {}
        self._inspectors: Dict[str, SchemaInspector] = {}

    def _load_questions(self) -> List[BenchmarkQuestion]:
        if not self.questions_path.exists():
            return []
        with open(self.questions_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [BenchmarkQuestion(**item) for item in data]

    def get_db(self, db_id: str) -> tuple[DatabaseEngine, SchemaInspector]:
        if db_id not in self._engines:
            db_file = self.databases_dir / f"{db_id}.sqlite"
            if not db_file.exists():
                raise FileNotFoundError(f"Database file not found: {db_file}")
            engine = DatabaseEngine(str(db_file))
            inspector = SchemaInspector(str(db_file))
            self._engines[db_id] = engine
            self._inspectors[db_id] = inspector
        return self._engines[db_id], self._inspectors[db_id]

    def evaluate_strategy(
        self,
        strategy: str,
        limit: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, EvaluationItemResult], None]] = None,
    ) -> tuple[StrategySummary, List[EvaluationItemResult]]:
        """Run benchmark evaluation for a given strategy."""
        questions_to_run = self.questions[:limit] if limit else self.questions
        results: List[EvaluationItemResult] = []

        for idx, q in enumerate(questions_to_run, 1):
            db_engine, inspector = self.get_db(q.db_id)
            start_t = time.perf_counter()
            pred_sql = ""
            iterations = 1
            err_msg = None

            try:
                if strategy == "zero_shot":
                    if ZeroShotSQLGenerator is not None:
                        gen = ZeroShotSQLGenerator(inspector=inspector, llm=self.llm)
                        gen_res = gen.generate(q.question)
                        pred_sql = gen_res.generated_sql
                    else:
                        resp = self.llm.generate(f"Schema:\n{inspector.to_compact_markdown()}\nQuestion: {q.question}")
                        pred_sql = resp.content.strip().replace("```sql", "").replace("```", "").strip()

                elif strategy == "few_shot":
                    if FewShotSQLGenerator is not None:
                        gen = FewShotSQLGenerator(inspector=inspector, llm=self.llm)
                        gen_res = gen.generate(q.question)
                        pred_sql = gen_res.generated_sql
                    else:
                        resp = self.llm.generate(f"Exemplars...\nQuestion: {q.question}")
                        pred_sql = resp.content.strip().replace("```sql", "").replace("```", "").strip()

                elif strategy == "cot_planner":
                    if CoTPlannerSQLGenerator is not None:
                        gen = CoTPlannerSQLGenerator(inspector=inspector, llm=self.llm)
                        gen_res = gen.generate(q.question)
                        pred_sql = gen_res.generated_sql
                    else:
                        resp = self.llm.generate(f"Plan and generate SQL: {q.question}")
                        pred_sql = resp.content.strip().replace("```sql", "").replace("```", "").strip()

                elif strategy == "self_correction":
                    if ZeroShotSQLGenerator is not None and SelfCorrectionChain is not None:
                        gen = ZeroShotSQLGenerator(inspector=inspector, llm=self.llm)
                        gen_res = gen.generate(q.question)
                        chain = SelfCorrectionChain(db_engine=db_engine, inspector=inspector, llm=self.llm, max_iterations=3)
                        corr_res = chain.run(q.question, initial_sql=gen_res.generated_sql)
                        pred_sql = corr_res.final_sql
                        iterations = corr_res.iterations_used
                        if not corr_res.success and corr_res.final_execution:
                            err_msg = corr_res.final_execution.error_message
                    else:
                        resp = self.llm.generate(f"Correct SQL for: {q.question}")
                        pred_sql = resp.content.strip().replace("```sql", "").replace("```", "").strip()

                elif strategy == "react_agent":
                    if ReActSQLAgent is not None:
                        agent = ReActSQLAgent(db_engine=db_engine, inspector=inspector, llm=self.llm, max_steps=6)
                        agent_res = agent.run(q.question)
                        pred_sql = agent_res.final_sql
                        iterations = max(1, agent_res.tool_calls_count)
                        if not agent_res.success and agent_res.final_execution:
                            err_msg = agent_res.final_execution.error_message
                    else:
                        resp = self.llm.generate(f"Agent solve: {q.question}")
                        pred_sql = resp.content.strip().replace("```sql", "").replace("```", "").strip()

                else:
                    raise ValueError(f"Unknown evaluation strategy: {strategy}")

            except Exception as e:
                err_msg = str(e)
                pred_sql = ""

            latency = (time.perf_counter() - start_t) * 1000.0

            # Calculate metrics
            em = calculate_exact_match(pred_sql, q.gold_sql)
            ex, pred_res, gold_res = calculate_execution_accuracy(db_engine, pred_sql, q.gold_sql)

            item = EvaluationItemResult(
                question_id=q.id,
                db_id=q.db_id,
                question=q.question,
                difficulty=q.difficulty,
                strategy=strategy,
                pred_sql=pred_sql,
                gold_sql=q.gold_sql,
                exact_match=em,
                execution_accuracy=ex,
                iterations=iterations,
                latency_ms=round(latency, 2),
                error_message=err_msg,
            )
            results.append(item)

            if progress_callback:
                progress_callback(idx, len(questions_to_run), item)

        summary = self._summarize_results(strategy, results)
        return summary, results

    def _summarize_results(self, strategy: str, results: List[EvaluationItemResult]) -> StrategySummary:
        total = len(results)
        if total == 0:
            return StrategySummary(
                strategy=strategy,
                total_questions=0,
                exact_match_count=0,
                execution_match_count=0,
                exact_match_accuracy_pct=0.0,
                execution_accuracy_pct=0.0,
                avg_correction_iterations=0.0,
                avg_latency_ms=0.0,
            )

        em_count = sum(1 for r in results if r.exact_match)
        ex_count = sum(1 for r in results if r.execution_accuracy)
        avg_iter = sum(r.iterations for r in results) / total
        avg_latency = sum(r.latency_ms for r in results) / total

        # Difficulty breakdown (normalizing extra-hard / extra_hard)
        diff_data: Dict[str, Dict[str, float]] = {}
        for diff_key in ["easy", "medium", "hard", "extra-hard"]:
            diff_items = [
                r for r in results
                if r.difficulty.lower().replace("_", "-") == diff_key
            ]
            if diff_items:
                d_total = len(diff_items)
                d_em = sum(1 for r in diff_items if r.exact_match)
                d_ex = sum(1 for r in diff_items if r.execution_accuracy)
                diff_data[diff_key] = {
                    "count": float(d_total),
                    "em_accuracy": round((d_em / d_total) * 100.0, 2),
                    "ex_accuracy": round((d_ex / d_total) * 100.0, 2),
                }

        # Database breakdown
        db_data: Dict[str, Dict[str, float]] = {}
        unique_dbs = sorted(list({r.db_id for r in results}))
        for db in unique_dbs:
            db_items = [r for r in results if r.db_id == db]
            if db_items:
                d_total = len(db_items)
                d_em = sum(1 for r in db_items if r.exact_match)
                d_ex = sum(1 for r in db_items if r.execution_accuracy)
                db_data[db] = {
                    "count": float(d_total),
                    "em_accuracy": round((d_em / d_total) * 100.0, 2),
                    "ex_accuracy": round((d_ex / d_total) * 100.0, 2),
                }

        return StrategySummary(
            strategy=strategy,
            total_questions=total,
            exact_match_count=em_count,
            execution_match_count=ex_count,
            exact_match_accuracy_pct=round((em_count / total) * 100.0, 2),
            execution_accuracy_pct=round((ex_count / total) * 100.0, 2),
            avg_correction_iterations=round(avg_iter, 2),
            avg_latency_ms=round(avg_latency, 2),
            difficulty_breakdown=diff_data,
            database_breakdown=db_data,
        )
