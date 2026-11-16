"""Evaluation metrics: Exact-Match (EM), Execution Accuracy (EX), and correction iteration statistics."""

from typing import List, Any, Tuple, Optional, Set
import sqlglot
from sqlglot import exp

from ..core.db_engine import DatabaseEngine, ExecutionResult


def normalize_sql(sql: str) -> str:
    """Normalize SQL syntax and formatting using sqlglot for robust comparison."""
    if not sql:
        return ""
    try:
        parsed = sqlglot.parse_one(sql.strip().rstrip(";"), read="sqlite")
        return parsed.sql(dialect="sqlite", pretty=False).lower()
    except Exception:
        # Fallback basic whitespace/case normalization
        return " ".join(sql.strip().rstrip(";").lower().split())


def calculate_exact_match(pred_sql: str, gold_sql: str) -> bool:
    """Computes whether normalized AST or canonical SQL representations match exactly."""
    norm_pred = normalize_sql(pred_sql)
    norm_gold = normalize_sql(gold_sql)
    return norm_pred == norm_gold


def normalize_result_rows(rows: List[List[Any]]) -> Set[Tuple[Any, ...]]:
    """Normalize row records into hashable set of tuples for set-comparison."""
    normalized = set()
    for row in rows:
        norm_row = []
        for val in row:
            if isinstance(val, float):
                norm_row.append(round(val, 4))
            elif isinstance(val, str):
                norm_row.append(val.strip().lower())
            else:
                norm_row.append(val)
        normalized.add(tuple(norm_row))
    return normalized


def calculate_execution_accuracy(
    db_engine: DatabaseEngine,
    pred_sql: str,
    gold_sql: str,
) -> Tuple[bool, Optional[ExecutionResult], Optional[ExecutionResult]]:
    """Execute both generated query and ground truth query; compare output row sets."""
    gold_res = db_engine.execute_query(gold_sql)
    pred_res = db_engine.execute_query(pred_sql)

    if not gold_res.success or not pred_res.success:
        return False, pred_res, gold_res

    # Check if results match
    # 1. Row count match
    if gold_res.row_count != pred_res.row_count:
        return False, pred_res, gold_res

    # 2. Check set equality of row contents (invariant to column ordering/alias)
    gold_set = normalize_result_rows(gold_res.rows)
    pred_set = normalize_result_rows(pred_res.rows)

    is_equal = (gold_set == pred_set)
    return is_equal, pred_res, gold_res
