"""Zero-Shot Schema-Aware SQL Generator."""

import time
from .base import BaseSQLGenerator, GenerationResult


class ZeroShotSQLGenerator(BaseSQLGenerator):
    """Generates SQL using zero-shot prompting with full schema context."""

    def build_prompt(self, question: str) -> str:
        schema_text = self.inspector.to_compact_markdown(include_samples=True)
        return f"""You are an expert database administrator and SQLite SQL specialist.
Given the following database schema, generate a single executable SQLite query that accurately answers the user question.

### Database Schema:
{schema_text}

### Instructions:
1. Return ONLY the executable SQL query enclosed in ```sql ... ``` code block.
2. Do not include introductory text, explanations, or markdown text outside the code block.
3. Use exact table and column names as defined in the schema.
4. Ensure proper table aliases and join conditions when joining multiple tables.
5. Use standard SQLite functions (e.g. COUNT, AVG, SUM, MAX, MIN, strftime, LIKE).

### Question:
{question}
"""

    def generate(self, question: str) -> GenerationResult:
        start_time = time.perf_counter()
        prompt = self.build_prompt(question)
        response = self.llm.generate(
            prompt=prompt,
            system_prompt="You are a SQL generation engine. Return only executable SQLite query.",
            temperature=0.0,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        sql = self.extract_sql(response.content)
        validation = self.validator.validate(sql)

        return GenerationResult(
            strategy="zero_shot",
            question=question,
            generated_sql=validation.normalized_sql or sql,
            raw_response=response.content,
            prompt_used=prompt,
            validation=validation,
            generation_time_ms=round(duration_ms, 2),
        )
