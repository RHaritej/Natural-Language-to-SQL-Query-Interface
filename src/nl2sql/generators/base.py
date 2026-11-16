"""Base SQL Generator interface."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from ..core.schema_inspector import SchemaInspector
from ..core.query_planner import QueryPlan, QueryPlanner
from ..core.validator import SQLValidator, ValidationResult
from ..llm.base import BaseLLMClient


class GenerationResult(BaseModel):
    """Output of a SQL generation attempt."""
    strategy: str  # "zero_shot", "few_shot", "cot_planner"
    question: str
    generated_sql: str
    raw_response: str
    prompt_used: str
    query_plan: Optional[QueryPlan] = None
    validation: Optional[ValidationResult] = None
    generation_time_ms: float = 0.0


class BaseSQLGenerator(ABC):
    """Abstract base class for schema-aware SQL generators."""

    def __init__(
        self,
        inspector: SchemaInspector,
        llm: BaseLLMClient,
        validator: Optional[SQLValidator] = None,
    ):
        self.inspector = inspector
        self.llm = llm
        self.validator = validator or SQLValidator(inspector=inspector)
        self.planner = QueryPlanner(inspector=inspector)

    @abstractmethod
    def generate(self, question: str) -> GenerationResult:
        """Generate SQL query from natural language question."""
        pass

    def extract_sql(self, raw_text: str) -> str:
        """Clean and extract SQL from raw LLM text output."""
        return self.validator.clean_markdown_fences(raw_text)
