"""Chain-of-Thought (CoT) SQL Generator with explicit Query Planning."""

import time
from .base import BaseSQLGenerator, GenerationResult


class CoTPlannerSQLGenerator(BaseSQLGenerator):
    """Generates SQL using structured Chain-of-Thought query planning."""

    def build_prompt(self, question: str) -> tuple[str, any]:
        schema_text = self.inspector.to_compact_markdown(include_samples=True)
        # Execute query planner
        plan = self.planner.plan(question)
        cot_plan_text = plan.to_cot_text()

        prompt = f"""You are an elite database architect and query planner specializing in SQLite.
Your task is to convert the natural language question into an optimized, executable SQLite query by adhering to the following step-by-step query plan.

### Database Schema:
{schema_text}

{cot_plan_text}

### Instructions:
1. Review the query plan carefully:
   - Use the designated relevant tables and foreign key join conditions.
   - Apply any detected aggregations (COUNT, AVG, SUM, MAX, MIN) and GROUP BY / HAVING clauses.
   - Formulate any nested subqueries or set operations (NOT IN, INTERSECT, etc.) as outlined in the plan.
2. In your response:
   - Provide your step-by-step reasoning in a brief 1-2 sentence summary.
   - Output the final SQLite query enclosed in ```sql ... ``` code block.

### Question:
{question}
"""
        return prompt, plan

    def generate(self, question: str) -> GenerationResult:
        start_time = time.perf_counter()
        prompt, plan = self.build_prompt(question)

        response = self.llm.generate(
            prompt=prompt,
            system_prompt="You are a Chain-of-Thought SQL query planner. First reason through the schema and join graph, then output the final SQLite query.",
            temperature=0.0,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        sql = self.extract_sql(response.content)
        validation = self.validator.validate(sql)

        return GenerationResult(
            strategy="cot_planner",
            question=question,
            generated_sql=validation.normalized_sql or sql,
            raw_response=response.content,
            prompt_used=prompt,
            query_plan=plan,
            validation=validation,
            generation_time_ms=round(duration_ms, 2),
        )
