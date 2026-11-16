"""Self-correction prompt chain that executes queries, captures errors, and iteratively fixes them."""

import time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from ..core.db_engine import DatabaseEngine, ExecutionResult
from ..core.schema_inspector import SchemaInspector
from ..core.validator import SQLValidator, ValidationResult
from ..llm.base import BaseLLMClient
from .error_analyzer import ErrorAnalyzer, ErrorDiagnosis


class CorrectionAttempt(BaseModel):
    """Record of a single attempt in the self-correction chain."""
    iteration: int
    sql: str
    validation: Optional[ValidationResult] = None
    execution: Optional[ExecutionResult] = None
    diagnosis: Optional[ErrorDiagnosis] = None
    thought: Optional[str] = None
    duration_ms: float = 0.0


class SelfCorrectionResult(BaseModel):
    """Overall outcome of the self-correction prompt chain."""
    success: bool
    question: str
    initial_sql: str
    final_sql: str
    iterations_used: int
    attempts: List[CorrectionAttempt] = Field(default_factory=list)
    final_execution: Optional[ExecutionResult] = None
    total_time_ms: float = 0.0


class SelfCorrectionChain:
    """Orchestrates iterative execution, error capture, and regeneration."""

    def __init__(
        self,
        db_engine: DatabaseEngine,
        inspector: SchemaInspector,
        llm: BaseLLMClient,
        max_iterations: int = 3,
        validator: Optional[SQLValidator] = None,
    ):
        self.db_engine = db_engine
        self.inspector = inspector
        self.llm = llm
        self.max_iterations = max_iterations
        self.validator = validator or SQLValidator(inspector=inspector)
        self.analyzer = ErrorAnalyzer(inspector=inspector)

    def run(self, question: str, initial_sql: str) -> SelfCorrectionResult:
        """Run self-correction loop starting from initial candidate SQL."""
        start_time = time.perf_counter()
        current_sql = initial_sql
        attempts: List[CorrectionAttempt] = []

        for iteration in range(1, self.max_iterations + 1):
            iter_start = time.perf_counter()
            cleaned_sql = self.validator.clean_markdown_fences(current_sql)
            
            # 1. Validation check
            val_result = self.validator.validate(cleaned_sql)
            if not val_result.is_valid:
                diagnosis = self.analyzer.diagnose_validation_error(val_result)
                exec_result = ExecutionResult(
                    success=False,
                    sql=cleaned_sql,
                    error_message="; ".join(val_result.all_errors),
                    error_type="VALIDATION_ERROR",
                )
            else:
                # 2. Execution on Database
                exec_result = self.db_engine.execute_query(val_result.normalized_sql or cleaned_sql)
                if exec_result.success:
                    # Successful execution!
                    attempts.append(
                        CorrectionAttempt(
                            iteration=iteration,
                            sql=val_result.normalized_sql or cleaned_sql,
                            validation=val_result,
                            execution=exec_result,
                            duration_ms=round((time.perf_counter() - iter_start) * 1000.0, 2),
                        )
                    )
                    total_time = (time.perf_counter() - start_time) * 1000.0
                    return SelfCorrectionResult(
                        success=True,
                        question=question,
                        initial_sql=initial_sql,
                        final_sql=val_result.normalized_sql or cleaned_sql,
                        iterations_used=iteration,
                        attempts=attempts,
                        final_execution=exec_result,
                        total_time_ms=round(total_time, 2),
                    )
                else:
                    diagnosis = self.analyzer.diagnose_execution_error(exec_result, cleaned_sql)

            # Record failed attempt
            attempts.append(
                CorrectionAttempt(
                    iteration=iteration,
                    sql=cleaned_sql,
                    validation=val_result,
                    execution=exec_result,
                    diagnosis=diagnosis,
                    duration_ms=round((time.perf_counter() - iter_start) * 1000.0, 2),
                )
            )

            # If we reached max iterations, stop
            if iteration >= self.max_iterations:
                break

            # 3. Request LLM correction
            current_sql = self._request_llm_fix(
                question=question,
                failed_sql=cleaned_sql,
                diagnosis=diagnosis,
                iteration=iteration,
            )

        total_time = (time.perf_counter() - start_time) * 1000.0
        return SelfCorrectionResult(
            success=False,
            question=question,
            initial_sql=initial_sql,
            final_sql=current_sql,
            iterations_used=len(attempts),
            attempts=attempts,
            final_execution=attempts[-1].execution if attempts else None,
            total_time_ms=round(total_time, 2),
        )

    def _request_llm_fix(
        self,
        question: str,
        failed_sql: str,
        diagnosis: ErrorDiagnosis,
        iteration: int,
    ) -> str:
        """Prompt the LLM with error diagnosis and request repaired query."""
        schema_text = self.inspector.to_compact_markdown(include_samples=True)

        prompt = f"""You are fixing an erroneous SQLite query for a database.
The user asked: "{question}"

### Target Database Schema:
{schema_text}

### Failed Query (Attempt {iteration}):
```sql
{failed_sql}
```

### Execution Error Encountered:
- Error Type: {diagnosis.error_type}
- Error Details: {diagnosis.raw_message}

### Repair Diagnostic Advice:
{diagnosis.suggested_fix}

### Task:
Regenerate a corrected, executable SQLite query that resolves this error and satisfies the original user question.
Return ONLY the corrected SQL query inside a ```sql ... ``` code block.
"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt="You are a SQL repair engine. Fix the query according to the provided diagnostic feedback.",
                temperature=0.0,
            )
            return self.validator.clean_markdown_fences(response.content)
        except Exception:
            # LLM unavailable — return empty string so caller records a failed attempt
            return ""
