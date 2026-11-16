# System Architecture: Natural Language to SQL Query Interface

## 1. Overview & High-Level Design

The **Natural Language to SQL (NL-to-SQL)** Query Interface is an enterprise-ready relational database assistant engineered around modular, pluggable subsystems. It translates conversational user inquiries into syntactically valid, schema-grounded, and read-only SQLite SQL queries, self-corrects runtime errors iteratively, allows autonomous tool-driven agent inspection, and explains execution output in plain English.

```
+---------------------------------------------------------------------------------------+
|                                Streamlit Web UI (app.py)                              |
|  [💬 Query Interface]   [🤖 ReAct Agent]   [📊 Benchmark Dashboard]   [🗂️ Schema Explorer] |
+---------------------------------------------------------------------------------------+
                                           │
                                           ▼
+---------------------------------------------------------------------------------------+
|                               Unified NL2SQLPipeline                                  |
|                                (src/nl2sql/pipeline.py)                               |
+---------------------------------------------------------------------------------------+
       │                      │                         │                      │
       ▼                      ▼                         ▼                      ▼
┌──────────────┐     ┌─────────────────┐       ┌─────────────────┐    ┌─────────────────┐
│ Schema       │     │ SQL Generators  │       │ Self-Correction │    │ ReAct SQL       │
│ Inspector    │     │                 │       │ Chain           │    │ Autonomous      │
│ & FK Graph   │     │ - Zero-Shot     │       │                 │    │ Agent           │
│              │     │ - Few-Shot      │       │ - ErrorAnalyzer │    │                 │
│              │     │ - CoT Planner   │       │ - RepairAdvisor │    │ - Tool Registry │
└──────────────┘     └─────────────────┘       └─────────────────┘    └─────────────────┘
       │                      │                         │                      │
       ▼                      ▼                         ▼                      ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                        AST & Safety Validator (sqlglot)                               │
│              - Disallow destructive statements (DROP/DELETE/UPDATE/INSERT)             │
│              - Column and Table existence validation against SchemaInspector          │
└───────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                        DatabaseEngine (Read-Only SQLite)                              │
│              - Foreign keys enforced (PRAGMA foreign_keys = ON)                       │
│              - Row normalization and structured ExecutionResult                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                           Natural Result Explainer                                    │
│              - Query breakdown + tabular row summary + business insights              │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Subsystems & Team Architecture

The system is developed across 4 dedicated subsystem modules:

### Subsystem 1: Core Engine & Multi-Provider LLM Abstraction
- **`DatabaseEngine` (`src/nl2sql/core/db_engine.py`)**: SQLite connector with read-only query execution, foreign keys enabled, row fetching, and structured execution error classification (`SYNTAX_ERROR`, `NO_SUCH_COLUMN`, `NO_SUCH_TABLE`, `AGGREGATE_ERROR`).
- **`SchemaInspector` (`src/nl2sql/core/schema_inspector.py`)**: Live schema introspection extracting tables, columns, primary keys, sample rows, and building a directed foreign-key graph with Breadth-First Search (BFS) join path discovery.
- **LLM Abstraction Layer (`src/nl2sql/llm/`)**: Base interface supporting:
  - `OllamaClient`: Local offline LLM inference (`llama3.2`, `mistral`, `qwen`).
  - `OpenAIClient`: OpenAI API models (`gpt-4o`, `gpt-4o-mini`).
  - `GeminiClient`: Google Gemini API (`gemini-1.5-flash`).
  - `MockLLMClient`: High-speed offline deterministic benchmark simulator.

### Subsystem 2: Schema-Aware Generators & Query Planning
- **`SQLValidator` (`src/nl2sql/core/validator.py`)**: AST-level parsing with `sqlglot` under SQLite dialect. Strips markdown fences, verifies read-only status, extracts referenced tables/columns, and compares against introspected schemas.
- **`QueryPlanner` (`src/nl2sql/core/query_planner.py`)**: Formulates multi-step Chain-of-Thought query plans:
  - Schema linking (entity extraction).
  - Join resolution via BFS on foreign key relationships.
  - Aggregation (`COUNT`, `SUM`, `AVG`, `MAX`, `MIN`), grouping, and having detection.
  - Subquery detection (aggregate comparisons like *above average*, set exclusion `NOT IN`, and set operations `INTERSECT`/`EXCEPT`).
- **Generators (`src/nl2sql/generators/`)**:
  - `ZeroShotSQLGenerator`: Schema DDL + question.
  - `FewShotSQLGenerator`: Exemplar demonstrations with complex multi-table joins.
  - `CoTPlannerSQLGenerator`: Interleaves query plan reasoning into generation prompt.

### Subsystem 3: Self-Correction Chain, ReAct Agent & Result Explainer
- **`SelfCorrectionChain` (`src/nl2sql/correction/`)**:
  - Executes candidate queries in sandbox mode.
  - Captures SQLite errors and diagnoses them via `ErrorAnalyzer`.
  - Injects diagnostic feedback and actionable repair tips back into LLM context.
  - Iterates up to `max_iterations` (default 3) until execution succeeds.
- **`ReActSQLAgent` (`src/nl2sql/agent/`)**:
  - Thought $\rightarrow$ Action $\rightarrow$ Observation reasoning loop.
  - Access to database tools: `list_tables`, `describe_table`, `sample_table_data`, `validate_query`, `execute_query`.
- **`ExplanationService` (`src/nl2sql/explainer/`)**:
  - Converts query structure and returned database records into conversational English for non-technical stakeholders.

### Subsystem 4: Benchmark, Evaluation Suite, Unified Pipeline & UI
- **`BenchmarkEvaluator` & `metrics.py` (`src/nl2sql/benchmark/`)**:
  - Exact-Match (EM): AST normalization with `sqlglot`.
  - Execution Accuracy (EX): Row-set equality invariant to order.
  - Full evaluation runner over 100 questions with JSON, HTML, and Markdown reports.
- **`NL2SQLPipeline` (`src/nl2sql/pipeline.py`)**:
  - Unified interface coordinating all subsystems into an end-to-end user query execution flow.
- **Streamlit Interface (`app.py`, `run_app.py`)**:
  - Interactive multi-tab web application for querying, agent monitoring, benchmark running, and schema exploration.
