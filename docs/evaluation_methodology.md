# Benchmark & Evaluation Methodology

## 1. Dataset Construction (Spider Benchmark Subset)

The benchmark evaluation dataset is modeled directly on the canonical **Spider cross-domain text-to-SQL benchmark**:
- **5 Relational Databases**:
  1. `concert_singer`: Entertainment domain (stadiums, singers, concerts, singer appearances).
  2. `car_1`: Automotive domain (continents, countries, car makers, models, vehicle specifications).
  3. `world_1`: Geographic & demographic domain (countries, cities, official languages).
  4. `employee_hire_evaluation`: Corporate domain (employees, retail shops, hiring history, performance evaluations).
  5. `student_transcripts_tracking`: Academic domain (students, addresses, degree programs, semesters, courses, transcripts).
- **100 Annotated Questions**:
  - Exactly **20 questions per database**.
  - Difficulty distribution spanning:
    - **Easy**: Single-table projections, simple filters, direct aggregations (`count(*)`, `avg()`, `max()`).
    - **Medium**: Two-table joins, `GROUP BY` aggregations, `ORDER BY ... LIMIT` patterns, scalar subqueries.
    - **Hard**: Multi-table joins (3+ tables), `HAVING` constraints, `NOT IN` subquery exclusions.
    - **Extra-Hard**: Set operations (`INTERSECT`, `EXCEPT`), nested aggregate comparisons, complex multi-entity joins.
- **Ground Truth Verification**:
  - Every single gold SQL query has been executed and verified against its database to guarantee valid syntax and non-empty result sets.

---

## 2. Evaluation Metrics

### Exact-Match Accuracy (EM %)
Exact-match measures whether the generated SQL query matches the ground truth query structurally:
1. **AST Normalization via `sqlglot`**:
   - Both predicted and ground-truth queries are parsed into AST representations using the SQLite dialect.
   - Whitespace differences, casing (`select` vs `SELECT`), unnecessary parentheses, and formatting quirks are normalized.
2. Canonical representations are compared for equivalence.

### Execution Accuracy (EX %)
Execution accuracy evaluates whether the generated query executes successfully and produces the identical data rows as the ground-truth query:
1. Both queries are executed against the target SQLite database via `DatabaseEngine`.
2. Returned rows are converted into sets of tuples to ensure order-insensitivity (unless `ORDER BY` is explicitly under test).
3. Numeric floating-point numbers are rounded to 4 decimal places to prevent spurious inequality due to machine precision.
4. String values are stripped of surrounding whitespace and normalized in casing.
5. If both queries yield identical sets of records, execution accuracy is scored as 1 (True); otherwise 0 (False).

### Average Correction Iterations
- Quantifies how many generation or self-correction passes were required:
  - Single-pass strategies (`zero_shot`, `few_shot`, `cot_planner`) have an iteration count of 1.00.
  - The `self_correction` chain runs additional repair iterations if initial execution fails.
  - The `react_agent` records the count of tool invocations taken before emitting the final query.

### Average Latency (ms)
- Wall-clock time measured using high-precision counters (`time.perf_counter()`), measuring total end-to-end processing per question.

---

## 3. Evaluated Strategies

1. **Zero-Shot**: Schema DDL + Question passed directly to the model.
2. **Few-Shot**: Includes 3 curated exemplars demonstrating projections, joins, and aggregations.
3. **Chain-of-Thought (CoT) Planner**: Generates schema linking, FK join paths, and subquery plans prior to SQL emission.
4. **Self-Correction Chain**: Iteratively tests queries in read-only sandbox mode, captures SQLite errors, and diagnoses fixes.
5. **Autonomous ReAct Agent**: Dynamic agent loop using inspection and execution tools to solve queries interactively.

---

## 4. Benchmark Execution CLI

To run the complete benchmark suite:
```bash
python scripts/run_evaluation.py --provider mock --strategy all --output-dir evaluation_results/
```

Results are automatically saved as:
- `evaluation_results/evaluation_report.md` (Markdown summary)
- `evaluation_results/evaluation_report.html` (Styled HTML dashboard)
- `evaluation_results/evaluation_results.json` (Machine-readable JSON data)
