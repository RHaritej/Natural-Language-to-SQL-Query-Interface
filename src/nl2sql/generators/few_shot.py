"""Few-Shot Schema-Aware SQL Generator."""

import time
from typing import List, Dict
from .base import BaseSQLGenerator, GenerationResult


FEW_SHOT_EXEMPLARS: List[Dict[str, str]] = [
    {
        "schema": """Table `stadium`:
  - Columns: Stadium_ID: INTEGER (PK), Location: TEXT, Name: TEXT, Capacity: INTEGER, Highest: INTEGER, Lowest: INTEGER, Average: INTEGER
Table `concert`:
  - Columns: concert_ID: INTEGER (PK), concert_Name: TEXT, Theme: TEXT, Stadium_ID: TEXT, Year: TEXT
  - Foreign Keys: `Stadium_ID` -> `stadium.Stadium_ID`""",
        "question": "What is the average and highest capacity of all stadiums?",
        "sql": "SELECT avg(Capacity), max(Capacity) FROM stadium",
    },
    {
        "schema": """Table `stadium`:
  - Columns: Stadium_ID: INTEGER (PK), Location: TEXT, Name: TEXT, Capacity: INTEGER
Table `concert`:
  - Columns: concert_ID: INTEGER (PK), concert_Name: TEXT, Theme: TEXT, Stadium_ID: TEXT, Year: TEXT
  - Foreign Keys: `Stadium_ID` -> `stadium.Stadium_ID`""",
        "question": "Show the stadium name and the number of concerts held in each stadium.",
        "sql": "SELECT T1.Name, count(T2.concert_ID) FROM stadium AS T1 JOIN concert AS T2 ON T1.Stadium_ID = T2.Stadium_ID GROUP BY T1.Name",
    },
    {
        "schema": """Table `singer`:
  - Columns: Singer_ID: INTEGER (PK), Name: TEXT, Country: TEXT, Song_Name: TEXT, Song_release_year: TEXT, Age: INTEGER, Is_male: INTEGER""",
        "question": "List the names of singers whose age is greater than the average age of all singers.",
        "sql": "SELECT Name FROM singer WHERE Age > (SELECT avg(Age) FROM singer)",
    },
    {
        "schema": """Table `stadium`:
  - Columns: Stadium_ID: INTEGER (PK), Location: TEXT, Name: TEXT, Capacity: INTEGER
Table `concert`:
  - Columns: concert_ID: INTEGER (PK), concert_Name: TEXT, Theme: TEXT, Stadium_ID: TEXT, Year: TEXT
  - Foreign Keys: `Stadium_ID` -> `stadium.Stadium_ID`""",
        "question": "Find the names of stadiums that have never hosted any concert.",
        "sql": "SELECT Name FROM stadium WHERE Stadium_ID NOT IN (SELECT Stadium_ID FROM concert)",
    },
    {
        "schema": """Table `car_names`:
  - Columns: MakeId: INTEGER (PK), Model: TEXT, Make: TEXT
Table `cars_data`:
  - Columns: Id: INTEGER (PK), MPG: REAL, Cylinders: INTEGER, Accelerate: REAL, Year: INTEGER""",
        "question": "What are the names and models of the top 3 cars with the fastest acceleration?",
        "sql": "SELECT T1.Make, T1.Model FROM car_names AS T1 JOIN cars_data AS T2 ON T1.MakeId = T2.Id ORDER BY T2.Accelerate ASC LIMIT 3",
    },
]


class FewShotSQLGenerator(BaseSQLGenerator):
    """Generates SQL using few-shot exemplars demonstrating joins, aggregation, and subqueries."""

    def build_prompt(self, question: str) -> str:
        schema_text = self.inspector.to_compact_markdown(include_samples=True)

        exemplar_sections = []
        for i, ex in enumerate(FEW_SHOT_EXEMPLARS, 1):
            exemplar_sections.append(
                f"### Example {i}:\nSchema:\n{ex['schema']}\nQuestion: {ex['question']}\nSQL:\n```sql\n{ex['sql']}\n```"
            )

        exemplars_text = "\n\n".join(exemplar_sections)

        return f"""You are an expert SQLite database developer.
Follow the pattern demonstrated in the examples below to translate the user question into an executable SQLite query.

{exemplars_text}

### Target Database Schema:
{schema_text}

### User Question:
{question}

Provide ONLY the executable SQLite query inside ```sql ... ``` code block.
"""

    def generate(self, question: str) -> GenerationResult:
        start_time = time.perf_counter()
        prompt = self.build_prompt(question)
        response = self.llm.generate(
            prompt=prompt,
            system_prompt="You are a SQL generator. Learn from the examples and generate the correct SQLite query.",
            temperature=0.0,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        sql = self.extract_sql(response.content)
        validation = self.validator.validate(sql)

        return GenerationResult(
            strategy="few_shot",
            question=question,
            generated_sql=validation.normalized_sql or sql,
            raw_response=response.content,
            prompt_used=prompt,
            validation=validation,
            generation_time_ms=round(duration_ms, 2),
        )
