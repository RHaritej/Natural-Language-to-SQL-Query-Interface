"""SQL Syntax, Schema, and Safety Validator using sqlglot and schema metadata."""

import re
from typing import List, Set, Optional, Tuple
from pydantic import BaseModel, Field
import sqlglot
from sqlglot import exp

from .schema_inspector import SchemaInspector


class ValidationResult(BaseModel):
    """Validation report for a generated SQL query."""
    is_valid: bool
    sql: str
    normalized_sql: Optional[str] = None
    syntax_error: Optional[str] = None
    schema_errors: List[str] = Field(default_factory=list)
    referenced_tables: List[str] = Field(default_factory=list)
    referenced_columns: List[str] = Field(default_factory=list)
    is_read_only: bool = True

    @property
    def all_errors(self) -> List[str]:
        errs = []
        if self.syntax_error:
            errs.append(f"Syntax Error: {self.syntax_error}")
        for se in self.schema_errors:
            errs.append(f"Schema Error: {se}")
        if not self.is_read_only:
            errs.append("Safety Error: Modifying or destructive queries are disallowed.")
        return errs


class SQLValidator:
    """Validates SQL query syntax, schema conformity, and safety against the target database."""

    def __init__(self, inspector: Optional[SchemaInspector] = None):
        self.inspector = inspector

    def clean_markdown_fences(self, sql: str) -> str:
        """Strip markdown code block fences if LLM wrapped SQL in ```sql ... ```."""
        cleaned = sql.strip()
        # Remove markdown fences
        cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        # Find first SELECT or WITH
        match = re.search(r"\b(SELECT|WITH)\b.*", cleaned, flags=re.IGNORECASE | re.DOTALL)
        if match:
            cleaned = match.group(0)
        return cleaned.strip().rstrip(";")

    def validate(self, sql: str) -> ValidationResult:
        """Perform comprehensive validation on the SQL query."""
        cleaned_sql = self.clean_markdown_fences(sql)
        if not cleaned_sql:
            return ValidationResult(
                is_valid=False,
                sql=sql,
                syntax_error="Empty SQL query.",
            )

        # 1. Parse with sqlglot for SQLite dialect
        try:
            parsed = sqlglot.parse_one(cleaned_sql, read="sqlite")
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                sql=cleaned_sql,
                syntax_error=str(e),
            )

        # 2. Check read-only / safety (disallow INSERT, UPDATE, DELETE, DROP, ALTER)
        is_select = isinstance(parsed, (exp.Select, exp.Union, exp.Intersect, exp.Except))
        if not is_select:
            # Check if it is a WITH (CTE) wrapping a select
            if isinstance(parsed, exp.Expression) and parsed.find(exp.Select):
                is_select = True

        if not is_select:
            return ValidationResult(
                is_valid=False,
                sql=cleaned_sql,
                is_read_only=False,
                syntax_error="Only SELECT queries are allowed.",
            )

        # 3. Extract referenced tables
        referenced_tables = [table.name for table in parsed.find_all(exp.Table)]
        # Filter out aliases if any
        referenced_columns = [col.name for col in parsed.find_all(exp.Column)]

        # 4. Schema validation against inspector (if provided)
        schema_errors = []
        if self.inspector:
            known_tables = {t.lower() for t in self.inspector.get_table_names()}
            for tbl in referenced_tables:
                if tbl and tbl.lower() not in known_tables:
                    # Check if it's a CTE alias
                    ctes = [cte.alias for cte in parsed.find_all(exp.CTE)]
                    if tbl not in ctes:
                        schema_errors.append(f"Table '{tbl}' does not exist in schema.")

        # 5. Format / normalize SQL
        try:
            normalized_sql = parsed.sql(dialect="sqlite", pretty=True)
        except Exception:
            normalized_sql = cleaned_sql

        is_valid = len(schema_errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            sql=cleaned_sql,
            normalized_sql=normalized_sql,
            schema_errors=schema_errors,
            referenced_tables=list(dict.fromkeys(referenced_tables)),
            referenced_columns=list(dict.fromkeys(referenced_columns)),
            is_read_only=True,
        )
