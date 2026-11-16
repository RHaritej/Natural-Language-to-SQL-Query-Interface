"""Query Planner module for join resolution, aggregation analysis, and subquery structuring."""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field

from .schema_inspector import SchemaInspector


class JoinStep(BaseModel):
    """Specification of a join between two tables."""
    from_table: str
    to_table: str
    condition: str
    join_type: str = "JOIN"


class AggregationSpec(BaseModel):
    """Aggregation operation details."""
    function: str  # COUNT, AVG, SUM, MAX, MIN
    column: Optional[str] = None
    group_by_columns: List[str] = Field(default_factory=list)
    having_clause: Optional[str] = None


class SubquerySpec(BaseModel):
    """Subquery / Nested query planning details."""
    subquery_type: str  # 'AGGREGATE_COMPARISON', 'EXCLUSION_NOT_IN', 'SET_OPERATION', 'CORRELATED'
    target_table: str
    rationale: str
    outer_condition: str


class QueryPlan(BaseModel):
    """Structured query execution plan created before SQL generation."""
    question: str
    relevant_tables: List[str] = Field(default_factory=list)
    target_columns: List[str] = Field(default_factory=list)
    join_steps: List[JoinStep] = Field(default_factory=list)
    filter_conditions: List[str] = Field(default_factory=list)
    aggregations: List[AggregationSpec] = Field(default_factory=list)
    subqueries: List[SubquerySpec] = Field(default_factory=list)
    order_by: Optional[str] = None
    limit: Optional[int] = None
    cot_reasoning_steps: List[str] = Field(default_factory=list)

    def to_cot_text(self) -> str:
        """Render plan as Chain-of-Thought text prompt section."""
        lines = ["### Query Plan (Chain-of-Thought):"]
        for i, step in enumerate(self.cot_reasoning_steps, 1):
            lines.append(f"{i}. {step}")
        return "\n".join(lines)


class QueryPlanner:
    """Analyzes questions against database schema to synthesize join, aggregate, and subquery plans."""

    def __init__(self, inspector: SchemaInspector):
        self.inspector = inspector

    def plan(self, question: str) -> QueryPlan:
        """Derive a comprehensive QueryPlan for the natural language question."""
        q_lower = question.lower()
        plan = QueryPlan(question=question)

        # 1. Identify relevant tables & columns (Schema Linking)
        relevant_tables, candidate_cols = self._link_schema(q_lower)
        plan.relevant_tables = relevant_tables
        plan.target_columns = candidate_cols
        plan.cot_reasoning_steps.append(
            f"Schema Linking: Identified relevant tables: {relevant_tables or 'None found, default to primary table'} and candidate attributes: {candidate_cols}."
        )

        # 2. Plan Joins across identified tables
        if len(relevant_tables) > 1:
            joins = self._plan_joins(relevant_tables)
            plan.join_steps = joins
            if joins:
                join_summary = ", ".join(f"{j.from_table} -> {j.to_table} ON {j.condition}" for j in joins)
                plan.cot_reasoning_steps.append(f"Join Planning: Required joins: {join_summary}.")
            else:
                plan.cot_reasoning_steps.append("Join Planning: Multiple tables needed but direct join path inferred via primary keys.")
        else:
            plan.cot_reasoning_steps.append("Join Planning: Single table query; no join required.")

        # 3. Detect Aggregations, Grouping, Ordering
        agg_spec, order_desc, limit_val = self._detect_aggregations_and_limits(q_lower, relevant_tables)
        if agg_spec:
            plan.aggregations.append(agg_spec)
            plan.cot_reasoning_steps.append(
                f"Aggregation Planning: Detected function '{agg_spec.function}' on column '{agg_spec.column}'"
                + (f" grouped by {agg_spec.group_by_columns}" if agg_spec.group_by_columns else "")
                + (f" having {agg_spec.having_clause}" if agg_spec.having_clause else "")
                + "."
            )
        if order_desc:
            plan.order_by = order_desc
            plan.cot_reasoning_steps.append(f"Ordering Planning: Order results by {order_desc}.")
        if limit_val:
            plan.limit = limit_val
            plan.cot_reasoning_steps.append(f"Limit Planning: Limit results to {limit_val} rows.")

        # 4. Detect Nested Queries / Subqueries
        subquery = self._detect_subqueries(q_lower, relevant_tables)
        if subquery:
            plan.subqueries.append(subquery)
            plan.cot_reasoning_steps.append(
                f"Nested Query Planning: Identified subquery type '{subquery.subquery_type}' for {subquery.target_table}: {subquery.rationale}"
            )

        return plan

    def _link_schema(self, q_lower: str) -> Tuple[List[str], List[str]]:
        """Link words in question to table and column names."""
        tables_scored: Dict[str, int] = {}
        matched_columns: Set[str] = set()

        for t_name, table in self.inspector.tables.items():
            t_clean = t_name.lower().replace("_", " ")
            score = 0
            # Check table name match
            if t_name.lower() in q_lower or t_clean in q_lower:
                score += 5

            # Check singular / plural forms
            if t_clean.rstrip("s") in q_lower:
                score += 4

            # Check column matches
            for col in table.columns:
                c_clean = col.name.lower().replace("_", " ")
                if col.name.lower() in q_lower or c_clean in q_lower:
                    score += 2
                    matched_columns.add(f"{t_name}.{col.name}")
                # Value matches
                for val in col.sample_values:
                    if str(val).lower() in q_lower and len(str(val)) > 2:
                        score += 3
                        matched_columns.add(f"{t_name}.{col.name}")

            if score > 0:
                tables_scored[t_name] = score

        # Sort tables by score
        sorted_tables = sorted(tables_scored.keys(), key=lambda t: tables_scored[t], reverse=True)
        if not sorted_tables and self.inspector.tables:
            sorted_tables = [next(iter(self.inspector.tables.keys()))]

        return sorted_tables, list(matched_columns)

    def _plan_joins(self, tables: List[str]) -> List[JoinStep]:
        """Find connecting join path among multiple tables."""
        if len(tables) < 2:
            return []

        join_steps: List[JoinStep] = []
        connected = {tables[0]}
        remaining = set(tables[1:])

        while remaining:
            best_path = None
            for c_tbl in list(connected):
                for r_tbl in list(remaining):
                    path = self.inspector.find_shortest_join_path(c_tbl, r_tbl)
                    if path and (best_path is None or len(path) < len(best_path)):
                        best_path = path

            if not best_path:
                # Disconnected or implicit
                break

            # Add each hop along the path
            for i in range(len(best_path) - 1):
                t1, t2 = best_path[i], best_path[i + 1]
                conds = self.inspector.get_join_conditions([t1, t2])
                cond_str = conds[0] if conds else f"{t1}.id = {t2}.{t1}_id"
                # Check if join step already recorded
                exists = any(
                    (j.from_table == t1 and j.to_table == t2) or (j.from_table == t2 and j.to_table == t1)
                    for j in join_steps
                )
                if not exists:
                    join_steps.append(
                        JoinStep(
                            from_table=t1,
                            to_table=t2,
                            condition=cond_str,
                            join_type="JOIN",
                        )
                    )
                connected.add(t2)
                remaining.discard(t2)

        return join_steps

    def _detect_aggregations_and_limits(
        self, q_lower: str, tables: List[str]
    ) -> Tuple[Optional[AggregationSpec], Optional[str], Optional[int]]:
        """Identify aggregate functions (COUNT, SUM, AVG, MAX, MIN), order and limit."""
        func = None
        col = None
        group_by = []
        having = None
        order_by = None
        limit = None

        if any(w in q_lower for w in ["how many", "number of", "count of", "total number"]):
            func = "COUNT"
            col = "*"
        elif any(w in q_lower for w in ["average", "avg", "mean"]):
            func = "AVG"
        elif any(w in q_lower for w in ["total", "sum of", "combined"]):
            func = "SUM"
        elif any(w in q_lower for w in ["maximum", "max", "highest", "most", "largest", "oldest", "greatest"]):
            func = "MAX"
        elif any(w in q_lower for w in ["minimum", "min", "lowest", "least", "smallest", "youngest"]):
            func = "MIN"

        # Group by hints
        if any(w in q_lower for w in ["each", "per", "every", "by each", "group by"]):
            for t_name in tables:
                t = self.inspector.tables.get(t_name)
                if t:
                    for c in t.columns:
                        if c.name.lower() in q_lower or c.name.lower().replace("_", " ") in q_lower:
                            group_by.append(f"{t_name}.{c.name}")

        # Limit and Order hints
        if "top" in q_lower:
            match = re.search(r"top\s+(\d+)", q_lower)
            limit = int(match.group(1)) if match else 1
            order_by = "DESC"
        elif "bottom" in q_lower:
            match = re.search(r"bottom\s+(\d+)", q_lower)
            limit = int(match.group(1)) if match else 1
            order_by = "ASC"
        elif any(w in q_lower for w in ["highest", "most", "maximum", "largest"]):
            limit = 1
            order_by = "DESC"
        elif any(w in q_lower for w in ["lowest", "least", "minimum", "smallest"]):
            limit = 1
            order_by = "ASC"

        agg_spec = AggregationSpec(function=func, column=col, group_by_columns=group_by, having_clause=having) if func else None
        return agg_spec, order_by, limit

    def _detect_subqueries(self, q_lower: str, tables: List[str]) -> Optional[SubquerySpec]:
        """Detect nested subquery patterns like 'above average', 'never had', 'not in'."""
        primary_table = tables[0] if tables else "table"

        if any(p in q_lower for p in ["more than average", "greater than average", "above average", "higher than average"]):
            return SubquerySpec(
                subquery_type="AGGREGATE_COMPARISON",
                target_table=primary_table,
                rationale="Requires comparison with aggregate scalar subquery (e.g. WHERE col > (SELECT AVG(col) ...))",
                outer_condition="WHERE value > (SELECT AVG(...))",
            )
        elif any(p in q_lower for p in ["less than average", "below average", "smaller than average"]):
            return SubquerySpec(
                subquery_type="AGGREGATE_COMPARISON",
                target_table=primary_table,
                rationale="Requires comparison with aggregate scalar subquery (e.g. WHERE col < (SELECT AVG(col) ...))",
                outer_condition="WHERE value < (SELECT AVG(...))",
            )
        elif any(p in q_lower for p in ["never", "do not have", "have not", "no concerts", "no matches", "without any", "not participate"]):
            return SubquerySpec(
                subquery_type="EXCLUSION_NOT_IN",
                target_table=primary_table,
                rationale="Requires set exclusion (e.g. WHERE id NOT IN (SELECT foreign_id ...) or NOT EXISTS / EXCEPT)",
                outer_condition="WHERE id NOT IN (SELECT ...)",
            )
        elif "both" in q_lower and "and" in q_lower:
            return SubquerySpec(
                subquery_type="SET_OPERATION",
                target_table=primary_table,
                rationale="Requires set intersection (INTERSECT) or multi-condition membership",
                outer_condition="INTERSECT or IN",
            )
        return None
