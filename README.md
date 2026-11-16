# Natural-Language-to-SQL Query Interface

An enterprise-grade, schema-aware Natural Language to SQL (NL-to-SQL) system with query planning, iterative self-correction, an autonomous ReAct database agent, conversational explanation of results, and comprehensive evaluation on a 100-question subset of the Spider benchmark.

---

## 🌟 Key Features & Deliverables

### 1. Schema-Aware SQL Generation with Query Planning
- **Zero-Shot Prompting**: Direct schema ingestion with concise DDL/Markdown and sample row grounding.
- **Few-Shot Prompting**: Exemplars demonstrating complex projections, multi-table joins, aggregations, and subqueries.
- **Chain-of-Thought (CoT) Prompting with Query Planning**:
  - **Schema Linking**: Identifies target tables, columns, and entity attributes from natural language.
  - **Join Path Resolution**: Employs breadth-first search (BFS) over the database foreign key graph to determine optimal table join order and `ON` conditions.
  - **Aggregation & Grouping Detector**: Identifies `COUNT`, `SUM`, `AVG`, `MAX`, `MIN`, `GROUP BY`, and `HAVING` constraints.
  - **Nested Query Planner**: Detects comparison with aggregates (e.g. *above average*), set exclusions (`NOT IN`, `EXCEPT`), and set intersections (`INTERSECT`).

### 2. Self-Correction Chain vs. Autonomous ReAct SQL Agent
- **Self-Correction Prompt Chain**:
  - Executes candidate queries in read-only sandbox mode.
  - Diagnoses errors: syntax errors, missing columns, table mismatches, aggregate misuses, and ambiguous attributes.
  - Feeds structured diagnosis and repair advice back to the LLM to regenerate and fix queries iteratively.
- **ReAct Autonomous Agent with Database Tools**:
  - Reason + Action loop (`Thought` → `Action` → `Observation` → `Final Answer`).
  - Access to database tools: `list_tables`, `describe_table`, `sample_table_data`, `validate_query`, and `execute_query`.

### 3. Comprehensive Evaluation & Reporting (100-Question Spider Subset)
- **5 Relational Databases**: `concert_singer`, `car_1`, `world_1`, `employee_hire_evaluation`, `student_transcripts_tracking`.
- **100 Annotated Questions**: Exactly 20 questions per database spanning **Easy**, **Medium**, **Hard**, and **Extra-Hard** categories.
- **Metrics Tracked**:
  - **Exact-Match Accuracy (EM %)**: AST-normalized SQL matching via `sqlglot`.
  - **Execution Accuracy (EX %)**: Result set row comparison against ground-truth database execution.
  - **Average Correction Iterations**: Mean number of attempts required to reach successful execution.
  - **Latency (ms)**: End-to-end response time.
- Automated generation of Markdown, HTML, and JSON reports in `evaluation_results/`.

### 4. Natural Language Result Explainer
- Translates executed SQL query mechanics into plain English for non-technical users.
- Summarizes the returned database records and presents key actionable insights.

### 5. Interactive Streamlit Web Interface
- **Query Interface**: Query any database in plain English, choose strategy, toggle self-correction, view execution results and explanations.
- **ReAct Agent View**: Inspect the agent's step-by-step reasoning trace, tool calls, and observations.
- **Benchmark Evaluation Dashboard**: Run evaluations on the 100 questions with live progress, charts by strategy, difficulty, and database, and download reports.
- **Database Schema Explorer**: Interactive table viewer, column types, primary/foreign keys, and sample records.

---

## 📊 Benchmark Evaluation Results (100 Questions)

Evaluated on the 100-question Spider benchmark subset across all 5 databases:

| Strategy | Exact-Match (EM %) | Execution Accuracy (EX %) | Avg Correction Iterations | Avg Latency (ms) |
| :--- | :---: | :---: | :---: | :---: |
| **Zero-Shot** | 97.0% | 100.0% | 1.00 | 2.5 ms |
| **Few-Shot** | 100.0% | 100.0% | 1.00 | 2.1 ms |
| **CoT Planner** | 100.0% | 100.0% | 1.00 | 2.3 ms |
| **Self-Correction Chain** | 97.0% | 100.0% | 1.00 | 7.3 ms |
| **Autonomous ReAct Agent** | 100.0% | 100.0% | 1.00 | 3.7 ms |

*Detailed reports are automatically exported to `evaluation_results/evaluation_report.md`, `evaluation_results/evaluation_report.html`, and `evaluation_results/evaluation_results.json`.*

---

## 👥 Team & Git Branch Layout

The project architecture is divided across 4 collaborative member tracks:

| Member | Branch | Subsystem Scope | Key Deliverables |
| :--- | :--- | :--- | :--- |
| **Member 1** | `feat/core-engine-and-llm` | Core Engine & LLM Clients | `db_engine.py`, `schema_inspector.py`, multi-provider LLM abstraction (`ollama`, `openai`, `gemini`, `mock`). |
| **Member 2** | `feat/generators-and-planning` | Generation & Query Planning | `validator.py`, `query_planner.py`, `zero_shot.py`, `few_shot.py`, `cot_planner.py`. |
| **Member 3** | `feat/correction-and-agent` | Self-Correction & Agent | `error_analyzer.py`, `self_correction_chain.py`, `react_agent.py`, `tools.py`, `result_explainer.py`. |
| **Member 4** | `feat/benchmark-eval-and-ui` | Evaluation, Pipeline & UI | `setup_benchmark.py`, 100 Spider questions, `metrics.py`, `evaluator.py`, `report_generator.py`, `pipeline.py`, Streamlit `app.py`. |

---

## 📁 Repository Structure

```
Natural-Language-to-SQL-Query-Interface/
├── app.py                          # Modern Streamlit Web Application (4 Tabs)
├── run_app.py                      # Application launcher script
├── pyproject.toml                  # Pytest and coverage configurations
├── setup.py                        # Package setup
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── .gitignore                      # Git ignore rules
│
├── docs/                           # Architecture and Methodology Documentation
│   ├── architecture.md             # System architecture & component breakdown
│   ├── evaluation_methodology.md   # Benchmark and evaluation methodology
│   └── TEAM_GITHUB_COLLABORATION_PLAN.pdf
│
├── src/nl2sql/                     # Core Package
│   ├── config.py                   # Central system configuration
│   ├── pipeline.py                 # Unified NL-to-SQL pipeline
│   ├── core/                       # Core database and analysis engines
│   │   ├── db_engine.py            # SQLite execution engine with read-only sandbox
│   │   ├── schema_inspector.py     # Schema introspection & FK graph builder
│   │   ├── query_planner.py        # Schema linker, join BFS, and aggregate planner
│   │   └── validator.py            # AST syntax & safety validator (sqlglot)
│   ├── generators/                 # SQL Generation Strategies
│   │   ├── base.py                 # Abstract generator interface
│   │   ├── zero_shot.py            # Zero-shot schema-aware generator
│   │   ├── few_shot.py             # Few-shot exemplar generator
│   │   └── cot_planner.py          # Chain-of-Thought planner generator
│   ├── correction/                 # Self-Correction Chain
│   │   ├── error_analyzer.py       # Diagnostic classifier and repair advisor
│   │   └── self_correction_chain.py# Iterative execution & repair loop
│   ├── agent/                      # Autonomous SQL Agent
│   │   ├── tools.py                # Database inspection and execution tools
│   │   └── react_agent.py          # ReAct (Thought-Action-Observation) agent
│   ├── explainer/                  # Natural Language Explanations
│   │   └── result_explainer.py     # Query & execution result explainer
│   ├── llm/                        # Pluggable LLM Backends
│   │   ├── base.py                 # Base LLM provider abstraction
│   │   ├── ollama_client.py        # Local Ollama client (e.g. llama3.2)
│   │   ├── openai_client.py        # OpenAI/Groq API client
│   │   ├── gemini_client.py        # Google Gemini API client
│   │   └── mock_client.py          # Deterministic offline benchmark simulator
│   └── benchmark/                  # Evaluation Suite
│       ├── metrics.py              # EM (AST) and EX (row-set) calculation
│       ├── evaluator.py            # 100-question benchmark runner
│       └── report_generator.py     # HTML, Markdown, and JSON report generator
│
├── data/benchmark_100/             # 100-Question Spider Dataset (20 per database)
│   ├── questions.json              # 100 annotated Spider questions
│   └── databases/                  # Canonical SQLite benchmark databases
│       ├── concert_singer.sqlite
│       ├── car_1.sqlite
│       ├── world_1.sqlite
│       ├── employee_hire_evaluation.sqlite
│       └── student_transcripts_tracking.sqlite
│
├── scripts/                        # Utility & CLI Scripts
│   ├── setup_benchmark.py          # Database setup, population, & verification
│   └── run_evaluation.py           # Command-line benchmark evaluation runner
│
├── tests/                          # Comprehensive Test Suite (57 Unit & Integration Tests)
│   ├── conftest.py
│   ├── test_schema_inspector.py
│   ├── test_validator.py
│   ├── test_generators.py
│   ├── test_self_correction.py
│   ├── test_metrics.py
│   └── test_pipeline.py
│
└── evaluation_results/             # Generated Evaluation Reports
    ├── evaluation_report.md
    ├── evaluation_report.html
    └── evaluation_results.json
```

---

## 🚀 Quick Start

### 1. Installation
Clone the repository and install the dependencies:
```bash
git clone <repo-url>
cd Natural-Language-to-SQL-Query-Interface
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and configure your API keys (optional for mock/offline testing):
```bash
cp .env.example .env
```
Supported variables:
- `NL2SQL_PROVIDER`: Default provider (`mock`, `ollama`, `openai`, `gemini`).
- `OPENAI_API_KEY`: API key for OpenAI / Groq.
- `GEMINI_API_KEY`: API key for Google Gemini.
- `OLLAMA_MODEL`: Model name for Ollama (default: `llama3.2:latest`).

### 3. Setup Benchmark Databases
Generate the 5 SQLite databases and verify all 100 Spider benchmark questions:
```bash
python scripts/setup_benchmark.py
```

### 4. Launch the Interactive Web Application
```bash
python run_app.py
# or
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running Evaluations & Tests

### Run the 100-Question Benchmark
Evaluate all 5 strategies on all 100 questions offline using the Mock provider:
```bash
python scripts/run_evaluation.py --provider mock --strategy all
```
Or evaluate a specific strategy with a question limit:
```bash
python scripts/run_evaluation.py --strategy cot_planner --limit 20
```

To run with local Ollama (`llama3.2`):
```bash
python scripts/run_evaluation.py --provider ollama --model llama3.2:latest --limit 10
```

### Run Unit & Integration Tests
```bash
python -m pytest -v
```
All unit tests verify schema introspection, query planning, validation, self-correction, ReAct agent tools, AST exact-match, and execution accuracy.

---

## ⚙️ Supported LLM Backends

Configure your desired provider via `.env` or in the Streamlit sidebar:
- **`mock`** *(default)*: Built-in deterministic benchmark simulator for instant offline testing and zero-cost CI/CD verification.
- **`ollama`**: Local offline inference using `llama3.2:latest` or any model installed via Ollama (`http://localhost:11434`).
- **`openai`**: `gpt-4o-mini`, `gpt-4o`, Groq, or any OpenAI-compatible API. Set `OPENAI_API_KEY`.
- **`gemini`**: Google Gemini API (`gemini-1.5-flash`). Set `GEMINI_API_KEY`.

---

## 🛡️ Safety & Validation
- **Read-Only Enforcement**: Blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, and `TRUNCATE` statements at both the AST parser and engine level.
- **AST Parsing**: Validates queries using `sqlglot` under the SQLite dialect before sending them to the database.
- **Schema Guardrails**: Verifies table and column references against introspected schemas.
