"""Natural language explanation generator for SQL queries and execution results."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ..core.db_engine import ExecutionResult
from ..llm.base import BaseLLMClient


class QueryAndResultExplanation(BaseModel):
    query_breakdown: str
    result_summary: str
    key_insights: List[str] = []


class ExplanationService:
    """Explains SQL logic and translates tabular execution results into conversational English."""

    def __init__(self, llm: BaseLLMClient):
        self.llm = llm

    def explain(
        self,
        question: str,
        sql: str,
        result: ExecutionResult,
    ) -> QueryAndResultExplanation:
        """Generate conversational explanation of both the query mechanism and the data returned."""
        if not result.success:
            return QueryAndResultExplanation(
                query_breakdown=f"The query could not execute successfully: {result.error_message}",
                result_summary="No data could be retrieved due to an execution error.",
                key_insights=[f"Error Type: {result.error_type}"],
            )

        # Prepare snippet of result data for LLM
        row_count = result.row_count
        cols = result.columns
        sample_rows = result.rows[:5]

        data_preview_lines = []
        data_preview_lines.append(f"Columns: {', '.join(cols)}")
        for r in sample_rows:
            data_preview_lines.append(str(r))
        if row_count == 0:
            data_preview_lines.append("(No matching records found)")
        elif row_count > 5:
            data_preview_lines.append(f"... ({row_count - 5} more rows omitted)")

        data_preview = "\n".join(data_preview_lines)

        prompt = f"""You are a helpful data analyst. Explain the following SQL query and its execution results to a non-technical user in plain, conversational English.

### User Question:
{question}

### Executed SQL Query:
```sql
{sql}
```

### Execution Results:
- Total rows returned: {row_count}
{data_preview}

### Format Your Output Exactly As Follows:
Query Breakdown: <1-2 sentences explaining what the SQL did: tables joined, conditions applied, sorting>
Result Summary: <1-3 sentences directly answering the user's question based on the returned data>
Key Insights:
- <insight 1>
- <insight 2>
"""

        try:
            resp = self.llm.generate(
                prompt=prompt,
                system_prompt="You are a data explanation assistant. Answer the user question accurately from the query and result.",
                temperature=0.0,
            )
            raw = resp.content

            # Parse sections
            breakdown = "The query retrieved matching records from the database."
            summary = f"Retrieved {row_count} rows matching the criteria."
            insights = []

            if "Query Breakdown:" in raw and "Result Summary:" in raw:
                parts = raw.split("Result Summary:")
                breakdown = parts[0].replace("Query Breakdown:", "").strip()
                rest = parts[1]
                if "Key Insights:" in rest:
                    summary_part, insights_part = rest.split("Key Insights:")
                    summary = summary_part.strip()
                    for line in insights_part.strip().split("\n"):
                        clean_line = line.strip().lstrip("-*•0123456789. ")
                        if clean_line:
                            insights.append(clean_line)
                else:
                    summary = rest.strip()
            else:
                summary = raw.strip()

            return QueryAndResultExplanation(
                query_breakdown=breakdown,
                result_summary=summary,
                key_insights=insights or [f"Found {row_count} total records in {result.execution_time_ms} ms."],
            )
        except Exception:
            # Deterministic fallback explanation
            return QueryAndResultExplanation(
                query_breakdown=f"The query accessed the relevant tables to answer '{question}' using standard filters and aggregations.",
                result_summary=f"The query executed successfully and returned {row_count} row(s).",
                key_insights=[f"Executed in {result.execution_time_ms}ms with {len(cols)} columns."],
            )
