"""Error classification and diagnostic guidance for self-correction."""

import re
from typing import Optional, List, Dict
from pydantic import BaseModel
from ..core.schema_inspector import SchemaInspector
from ..core.db_engine import ExecutionResult
from ..core.validator import ValidationResult


class ErrorDiagnosis(BaseModel):
    """Categorized diagnosis and repair advice for a failing SQL query."""
    error_type: str
    raw_message: str
    explanation: str = ""
    suggested_fix: str
    relevant_tables: List[str] = []
    relevant_columns: List[str] = []


class ErrorAnalyzer:
    """Diagnoses validation and execution errors to supply constructive feedback to LLM."""

    def __init__(self, inspector: SchemaInspector):
        self.inspector = inspector

    def diagnose_validation_error(self, validation: ValidationResult) -> ErrorDiagnosis:
        if validation.syntax_error:
            return ErrorDiagnosis(
                error_type="SYNTAX_ERROR",
                raw_message=validation.syntax_error,
                explanation="The query has invalid SQLite syntax or structure.",
                suggested_fix="Check SQLite syntax carefully. Ensure matching parentheses, valid SELECT clauses, and correct keyword placement.",
            )
        if validation.schema_errors:
            err_str = "; ".join(validation.schema_errors)
            valid_tables = ", ".join(self.inspector.get_table_names())
            missing_tables = re.findall(r"Table '([^']+)' does not exist", err_str)
            return ErrorDiagnosis(
                error_type="SCHEMA_ERROR",
                raw_message=err_str,
                explanation="One or more referenced tables or columns do not exist in the database schema.",
                suggested_fix=f"You referenced a non-existent table. Valid tables in this database are: [{valid_tables}].",
                relevant_tables=missing_tables,
            )
        if not validation.is_read_only:
            return ErrorDiagnosis(
                error_type="SCHEMA_ERROR",
                raw_message="Disallowed mutating operation in query.",
                explanation="Non-query or modifying statement detected in read-only environment.",
                suggested_fix="Only read-only SELECT queries are permitted. Remove any data manipulation statements.",
            )
        return ErrorDiagnosis(
            error_type="UNKNOWN_VALIDATION_ERROR",
            raw_message="Unknown query validation failure.",
            explanation="The query failed AST validation checks against the target schema.",
            suggested_fix="Re-examine the schema and regenerate standard SQLite query.",
        )

    def diagnose_execution_error(self, exec_result: ExecutionResult, failed_sql: str) -> ErrorDiagnosis:
        msg = exec_result.error_message or ""
        msg_lower = msg.lower()
        err_type = (exec_result.error_type or "").upper()

        # 1. No such column
        if "no such column" in msg_lower or err_type == "NO_SUCH_COLUMN":
            col_match = re.search(r"no such column:\s*([^\s]+)", msg, flags=re.IGNORECASE)
            bad_col = col_match.group(1) if col_match else "unknown"
            
            # Find closest matching real column
            advice_list = []
            rel_tables = []
            for t_name, table in self.inspector.tables.items():
                for c in table.columns:
                    advice_list.append(f"{t_name}.{c.name}")
                    if c.name.lower() == bad_col.lower() or bad_col.lower() in c.name.lower():
                        rel_tables.append(t_name)

            return ErrorDiagnosis(
                error_type="NO_SUCH_COLUMN",
                raw_message=msg,
                explanation=f"Column '{bad_col}' was referenced in the query but does not exist in the database.",
                suggested_fix=(
                    f"The column '{bad_col}' does not exist in the database. "
                    f"Review the schema and use one of the actual columns: {advice_list[:10]}."
                ),
                relevant_tables=list(dict.fromkeys(rel_tables)),
                relevant_columns=[bad_col],
            )

        # 2. No such table
        if "no such table" in msg_lower or err_type == "NO_SUCH_TABLE":
            tbl_match = re.search(r"no such table:\s*([^\s]+)", msg, flags=re.IGNORECASE)
            bad_tbl = tbl_match.group(1) if tbl_match else "unknown"
            valid_tables = list(self.inspector.tables.keys())
            return ErrorDiagnosis(
                error_type="NO_SUCH_TABLE",
                raw_message=msg,
                explanation=f"Table '{bad_tbl}' does not exist in the target database schema.",
                suggested_fix=f"Table '{bad_tbl}' does not exist. Choose from the available tables: {valid_tables}.",
                relevant_tables=[bad_tbl],
            )

        # 3. Ambiguous column
        if "ambiguous" in msg_lower or err_type == "AMBIGUOUS_COLUMN":
            ambig_match = re.search(r"ambiguous column(?:\s+name)?:\s*([^\s]+)", msg, flags=re.IGNORECASE)
            ambig_col = ambig_match.group(1) if ambig_match else "unknown"
            return ErrorDiagnosis(
                error_type="AMBIGUOUS_COLUMN",
                raw_message=msg,
                explanation=f"Column '{ambig_col}' is present in more than one joined table without explicit table qualification.",
                suggested_fix="A column appears in multiple joined tables. Prefix every column with its table name or alias (e.g. T1.id, T2.id).",
                relevant_columns=[ambig_col] if ambig_col != "unknown" else [],
            )

        # 4. Aggregate misuse
        if "misuse of aggregate" in msg_lower or err_type in ("AGGREGATE_ERROR", "AGGREGATE_MISUSE"):
            return ErrorDiagnosis(
                error_type="AGGREGATE_MISUSE",
                raw_message=msg,
                explanation="An aggregate function (such as COUNT, AVG, SUM) was placed in a WHERE clause where it is not permitted.",
                suggested_fix="Aggregate functions like COUNT/AVG cannot be placed in WHERE clauses. Use a HAVING clause or a scalar subquery (e.g. WHERE col > (SELECT avg(col) ...)).",
            )

        # 5. Syntax / near error
        if "syntax error" in msg_lower or "near " in msg_lower or err_type == "SYNTAX_ERROR":
            return ErrorDiagnosis(
                error_type="SYNTAX_ERROR",
                raw_message=msg,
                explanation="The SQLite parser encountered invalid SQL syntax.",
                suggested_fix="SQLite syntax error occurred. Check clause order: SELECT -> FROM -> JOIN ON -> WHERE -> GROUP BY -> HAVING -> ORDER BY -> LIMIT.",
            )

        # 6. Schema error
        if "schema" in msg_lower or err_type == "SCHEMA_ERROR":
            return ErrorDiagnosis(
                error_type="SCHEMA_ERROR",
                raw_message=msg,
                explanation="The query references schema elements that violate relational constraints or definitions.",
                suggested_fix="Verify relational keys, join conditions, and table names against the schema.",
            )

        # 7. Default
        return ErrorDiagnosis(
            error_type="EXECUTION_ERROR",
            raw_message=msg,
            explanation="The query failed during execution on the SQLite engine.",
            suggested_fix="The query failed during execution. Re-read the database schema carefully and simplify the query.",
        )
