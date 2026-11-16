"""Streamlit Web UI for the Natural Language to SQL Query Interface."""

import sys
import json
from pathlib import Path
import streamlit as st
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nl2sql.config import DATABASES_DIR, QUESTIONS_FILE, RESULTS_DIR, SystemConfig
from nl2sql.pipeline import NL2SQLPipeline
from nl2sql.llm import get_llm_client
from nl2sql.benchmark.evaluator import BenchmarkEvaluator, StrategySummary
from nl2sql.benchmark.report_generator import generate_markdown_report, generate_html_report
from nl2sql.core.schema_inspector import SchemaInspector


# ─── Streamlit Page Config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="NL→SQL Query Interface",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main-title { font-size: 2.2rem; font-weight: 700; color: #2d6a4f; }
  .sub-title  { font-size: 1rem; color: #6c757d; margin-bottom: 1.5rem; }
  .sql-box    { background: #1e1e2e; color: #cdd6f4; padding: 16px; border-radius: 8px; font-family: monospace; }
  .success-badge { background: #d1fae5; color: #065f46; padding: 4px 10px; border-radius: 999px; font-weight: 600; }
  .error-badge   { background: #fee2e2; color: #991b1b; padding: 4px 10px; border-radius: 999px; font-weight: 600; }
  .stTabs [data-baseweb="tab"] { font-size: 0.95rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ─── Helper Functions ─────────────────────────────────────────────────────────

@st.cache_resource
def load_pipeline(db_path: str, provider: str, model: str) -> NL2SQLPipeline:
    cfg = SystemConfig(provider=provider, ollama_model=model)
    return NL2SQLPipeline(db_path=db_path, config=cfg)


@st.cache_resource
def load_inspector(db_path: str) -> SchemaInspector:
    return SchemaInspector(db_path)


def get_available_databases() -> dict:
    """Return available databases as {display_name: path}."""
    dbs = {}
    if DATABASES_DIR.exists():
        for f in sorted(DATABASES_DIR.glob("*.sqlite")):
            dbs[f.stem] = str(f)
    return dbs


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    provider = st.selectbox("LLM Provider", ["mock", "ollama", "openai", "gemini"], index=0)
    model_name = st.text_input(
        "Model Name",
        value="mock-deterministic" if provider == "mock" else ("llama3.2:latest" if provider == "ollama" else "gpt-4o-mini"),
    )

    st.divider()
    st.markdown("## 🗄️ Database")
    available_dbs = get_available_databases()

    if not available_dbs:
        st.warning("No benchmark databases found. Run `python scripts/setup_benchmark.py` first.")
        selected_db_name = None
        selected_db_path = None
    else:
        selected_db_name = st.selectbox("Select Database", list(available_dbs.keys()))
        selected_db_path = available_dbs[selected_db_name]

    st.divider()
    st.markdown("## 🛠️ Query Settings")
    strategy = st.selectbox("Generation Strategy", ["cot_planner", "zero_shot", "few_shot"], index=0)
    use_correction = st.toggle("Enable Self-Correction", value=True)
    explain = st.toggle("Explain Results", value=True)
    max_corrections = st.slider("Max Correction Iterations", 1, 5, 3)

    st.divider()
    st.markdown("### 📖 Strategy Guide")
    st.caption("**Zero-Shot**: Direct schema + question.")
    st.caption("**Few-Shot**: Learn from SQL examples.")
    st.caption("**CoT Planner**: Chain-of-Thought query plan.")
    st.caption("**Self-Correction**: Iterative error fixing.")
    st.caption("**ReAct Agent**: Tool-using autonomous agent.")


# ─── Main Area ────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🔍 Natural Language → SQL</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Schema-Aware SQL generation with Self-Correction · ReAct Agent · Benchmark Evaluation</div>', unsafe_allow_html=True)

main_tabs = st.tabs(["💬 Query Interface", "🤖 ReAct Agent", "📊 Benchmark Evaluation", "🗂️ Schema Explorer"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: Query Interface
# ══════════════════════════════════════════════════════════════════════════════
with main_tabs[0]:
    st.subheader("Ask a Question in Natural Language")
    col1, col2 = st.columns([3, 1])
    with col1:
        question = st.text_area(
            "Your question:",
            placeholder="e.g. How many singers are from the United States?",
            height=90,
            key="main_question",
        )
    with col2:
        st.markdown("**Quick Examples**")
        example_questions = [
            "How many singers do we have?",
            "Show stadiums that never held a concert.",
            "List the top 3 singers by age.",
            "Find singers above average age.",
            "Show each stadium's name and concert count.",
        ]
        for eq in example_questions:
            if st.button(eq[:45], key=f"ex_{eq[:10]}"):
                st.session_state["main_question"] = eq
                st.rerun()

    run_col, strategy_info = st.columns([1, 2])
    with run_col:
        run_clicked = st.button("▶ Generate & Execute", type="primary", use_container_width=True)
    with strategy_info:
        st.info(f"**Strategy:** `{strategy}` | **Self-Correction:** {'✅' if use_correction else '❌'} | **Explain:** {'✅' if explain else '❌'}")

    if run_clicked and question and selected_db_path:
        try:
            with st.spinner("Generating SQL & executing query..."):
                pipeline = load_pipeline(selected_db_path, provider, model_name)
                pipeline.config.max_correction_iterations = max_corrections
                result = pipeline.run(question, strategy=strategy, use_self_correction=use_correction, explain_results=explain)
        except Exception as e:
            st.error(f"❌ Execution Error: {e}")
            st.stop()

        # Results
        result_tabs = st.tabs(["📋 Query & Results", "🔄 Correction Chain", "💡 Explanation", "🧪 Raw Details"])

        with result_tabs[0]:
            sql_col, stat_col = st.columns([2, 1])
            with sql_col:
                st.markdown("**Generated SQL**")
                st.code(result.final_sql or result.generated_sql, language="sql")
            with stat_col:
                badge = "success-badge" if result.success else "error-badge"
                st.markdown(f'**Status:** <span class="{badge}">{"✅ SUCCESS" if result.success else "❌ FAILED"}</span>', unsafe_allow_html=True)
                if result.execution:
                    st.metric("Rows Returned", result.execution.row_count)
                    st.metric("Latency", f"{result.execution.execution_time_ms:.1f} ms")
                    st.metric("Total Time", f"{result.total_time_ms:.0f} ms")

            if result.execution and result.execution.success and result.execution.rows:
                st.markdown("**Results**")
                df = pd.DataFrame(result.execution.rows, columns=result.execution.columns)
                st.dataframe(df, use_container_width=True)
            elif result.execution and not result.execution.success:
                st.error(f"❌ {result.execution.error_message}")

        with result_tabs[1]:
            if result.correction:
                corr = result.correction
                st.metric("Iterations Used", corr.iterations_used)
                st.metric("Final Status", "✅ Corrected" if corr.success else "❌ Exhausted")
                for attempt in corr.attempts:
                    with st.expander(f"Attempt {attempt.iteration} — {'✅' if attempt.execution and attempt.execution.success else '❌'}"):
                        st.code(attempt.sql, language="sql")
                        if attempt.diagnosis:
                            st.warning(f"**Error:** [{attempt.diagnosis.error_type}] {attempt.diagnosis.raw_message}")
                            st.info(f"**Fix Advice:** {attempt.diagnosis.suggested_fix}")
            else:
                st.info("Self-correction was not enabled for this query.")

        with result_tabs[2]:
            if result.explanation:
                exp = result.explanation
                st.markdown("#### Query Breakdown")
                st.write(exp.query_breakdown)
                st.markdown("#### Result Summary")
                st.success(exp.result_summary)
                if exp.key_insights:
                    st.markdown("#### Key Insights")
                    for insight in exp.key_insights:
                        st.markdown(f"- {insight}")
            else:
                st.info("Enable 'Explain Results' in sidebar to see natural language explanations.")

        with result_tabs[3]:
            st.markdown("**Initial Generated SQL**")
            st.code(result.generated_sql, language="sql")
            if result.generation and result.generation.query_plan:
                st.markdown("**Query Plan (CoT)**")
                st.text(result.generation.query_plan.to_cot_text())


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: ReAct Agent
# ══════════════════════════════════════════════════════════════════════════════
with main_tabs[1]:
    st.subheader("🤖 Autonomous ReAct SQL Agent")
    st.caption("The agent inspects the schema, formulates candidate queries, tests them with database tools, and self-refines.")

    agent_question = st.text_area(
        "Agent Question:",
        placeholder="e.g. Find singers who appeared in both 2014 and 2015 concerts.",
        height=80,
        key="agent_q",
    )
    agent_run = st.button("🚀 Run Agent", type="primary")

    if agent_run and agent_question and selected_db_path:
        try:
            with st.spinner("Agent is reasoning and using database tools..."):
                pipeline = load_pipeline(selected_db_path, provider, model_name)
                agent_result = pipeline.run_agent(agent_question, explain_results=explain)
        except Exception as e:
            st.error(f"❌ Agent Error: {e}")
            st.stop()

        status_badge = "success-badge" if agent_result.success else "error-badge"
        st.markdown(f'**Agent Status:** <span class="{status_badge}">{"✅ SUCCESS" if agent_result.success else "❌ FAILED"}</span>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Agent Steps", len(agent_result.agent_run.steps) if agent_result.agent_run else 0)
        c2.metric("Tool Calls", agent_result.agent_run.tool_calls_count if agent_result.agent_run else 0)
        c3.metric("Total Time", f"{agent_result.total_time_ms:.0f} ms")

        st.markdown("**Final SQL**")
        st.code(agent_result.agent_run.final_sql if agent_result.agent_run else "No SQL", language="sql")

        if agent_result.agent_run:
            ar = agent_result.agent_run
            if ar.final_execution and ar.final_execution.success and ar.final_execution.rows:
                df = pd.DataFrame(ar.final_execution.rows, columns=ar.final_execution.columns)
                st.markdown("**Results**")
                st.dataframe(df, use_container_width=True)

            st.markdown("**Agent Reasoning Steps (Thought / Action / Observation)**")
            for step in ar.steps:
                with st.expander(f"Step {step.step_number} — {step.action or 'Final Answer'}"):
                    if step.thought:
                        st.markdown(f"**Thought:** {step.thought}")
                    if step.action:
                        st.markdown(f"**Action:** `{step.action}`")
                        st.json(step.action_input or {})
                    if step.observation:
                        st.markdown("**Observation:**")
                        try:
                            st.json(json.loads(step.observation))
                        except Exception:
                            st.text(step.observation)

        if agent_result.explanation:
            st.markdown("**Natural Language Explanation**")
            st.info(agent_result.explanation.result_summary)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: Benchmark Evaluation
# ══════════════════════════════════════════════════════════════════════════════
with main_tabs[2]:
    st.subheader("📊 Benchmark Evaluation (100-Question Spider Subset)")

    saved_results_file = RESULTS_DIR / "evaluation_results.json"
    has_saved_results = saved_results_file.exists()

    col_bench_top1, col_bench_top2 = st.columns([2, 1])
    with col_bench_top1:
        st.markdown("Run a live benchmark evaluation or load pre-computed evaluation reports.")
    with col_bench_top2:
        load_saved = st.button("📂 Load Saved Evaluation Results", use_container_width=True, disabled=not has_saved_results)

    eval_col1, eval_col2 = st.columns(2)
    with eval_col1:
        eval_strategies = st.multiselect(
            "Strategies to Evaluate:",
            ["zero_shot", "few_shot", "cot_planner", "self_correction", "react_agent"],
            default=["zero_shot", "cot_planner"],
        )
        eval_limit = st.number_input("Questions per Strategy (max 100):", min_value=1, max_value=100, value=10)
    with eval_col2:
        st.info("""
**Evaluation Metrics**
- **EM**: Exact-Match (normalized AST comparison with `sqlglot`)
- **EX**: Execution Accuracy (identical row set comparison)
- **Avg Iter**: Mean generation and correction passes
- **Avg Latency**: Wall-clock response time per question
        """)

    run_eval = st.button("🏁 Run Live Evaluation", type="primary", disabled=not eval_strategies)

    displayed_summaries = None
    displayed_results = None

    if load_saved and has_saved_results:
        with open(saved_results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        displayed_summaries = [StrategySummary(**s) for s in data.get("summaries", [])]
        displayed_results = {
            strat: [r for r in rows]
            for strat, rows in data.get("per_strategy_results", {}).items()
        }
        st.success(f"Loaded benchmark evaluation results from `{saved_results_file}`!")

    elif run_eval and eval_strategies:
        if not QUESTIONS_FILE.exists():
            st.warning("Setting up benchmark data first...")
            import subprocess
            subprocess.run([sys.executable, "scripts/setup_benchmark.py"])
            st.rerun()

        cfg = SystemConfig(provider=provider, ollama_model=model_name)
        llm = get_llm_client(cfg)
        evaluator = BenchmarkEvaluator(QUESTIONS_FILE, DATABASES_DIR, llm)

        all_summaries = []
        all_results = {}

        for strat in eval_strategies:
            progress_bar = st.progress(0, text=f"Evaluating `{strat}`...")

            def progress_cb(idx, total, item, bar=progress_bar, s=strat):
                bar.progress(idx / total, text=f"`{s}`: {idx}/{total} — Q{item.question_id}")

            summary, results = evaluator.evaluate_strategy(strat, limit=eval_limit, progress_callback=progress_cb)
            progress_bar.empty()
            all_summaries.append(summary)
            all_results[strat] = results

        displayed_summaries = all_summaries
        displayed_results = all_results

    if displayed_summaries:
        # Summary metrics
        st.markdown("### 📈 Strategy Comparison Summary")
        summary_rows = []
        chart_data_em = {}
        chart_data_ex = {}

        for s in displayed_summaries:
            summary_rows.append({
                "Strategy": s.strategy,
                "Total Qs": s.total_questions,
                "Exact-Match (%)": s.exact_match_accuracy_pct,
                "Execution Acc (%)": s.execution_accuracy_pct,
                "Avg Corrections": s.avg_correction_iterations,
                "Avg Latency (ms)": s.avg_latency_ms,
            })
            chart_data_em[s.strategy] = s.exact_match_accuracy_pct
            chart_data_ex[s.strategy] = s.execution_accuracy_pct

        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

        # Charts: Strategy Performance
        st.markdown("### 📊 Accuracy by Strategy (EM% vs EX%)")
        df_chart = pd.DataFrame({
            "Exact Match (EM %)": chart_data_em,
            "Execution Accuracy (EX %)": chart_data_ex,
        })
        st.bar_chart(df_chart)

        # Charts: Difficulty Breakdown
        st.markdown("### 🎯 Accuracy by Difficulty Level")
        diff_chart_data = {}
        for s in displayed_summaries:
            for diff, stats in s.difficulty_breakdown.items():
                label = f"{s.strategy} [{diff}]"
                diff_chart_data[label] = {
                    "EM %": stats.get("em_accuracy", 0.0),
                    "EX %": stats.get("ex_accuracy", 0.0),
                }
        if diff_chart_data:
            st.bar_chart(pd.DataFrame.from_dict(diff_chart_data, orient="index"))

        # Charts: Database Breakdown
        st.markdown("### 🗄️ Accuracy by Database")
        db_chart_data = {}
        for s in displayed_summaries:
            for db_name, stats in s.database_breakdown.items():
                label = f"{s.strategy} [{db_name}]"
                db_chart_data[label] = {
                    "EM %": stats.get("em_accuracy", 0.0),
                    "EX %": stats.get("ex_accuracy", 0.0),
                }
        if db_chart_data:
            st.bar_chart(pd.DataFrame.from_dict(db_chart_data, orient="index"))

        # Per-strategy question drilldown
        st.markdown("### 🔍 Question Level Drilldown")
        for s in displayed_summaries:
            results_list = displayed_results.get(s.strategy, [])
            with st.expander(f"**{s.strategy}** — EM: {s.exact_match_accuracy_pct:.1f}% | EX: {s.execution_accuracy_pct:.1f}% ({len(results_list)} queries)"):
                drill_rows = []
                for r in results_list:
                    # Dict or EvaluationItemResult
                    q_id = r["question_id"] if isinstance(r, dict) else r.question_id
                    q_diff = r["difficulty"] if isinstance(r, dict) else r.difficulty
                    q_db = r["db_id"] if isinstance(r, dict) else r.db_id
                    q_text = r["question"] if isinstance(r, dict) else r.question
                    q_em = r["exact_match"] if isinstance(r, dict) else r.exact_match
                    q_ex = r["execution_accuracy"] if isinstance(r, dict) else r.execution_accuracy
                    q_pred = r["pred_sql"] if isinstance(r, dict) else r.pred_sql
                    q_gold = r["gold_sql"] if isinstance(r, dict) else r.gold_sql
                    q_lat = r["latency_ms"] if isinstance(r, dict) else r.latency_ms

                    drill_rows.append({
                        "ID": q_id,
                        "Database": q_db,
                        "Difficulty": q_diff,
                        "Question": q_text[:60],
                        "EM": "✅" if q_em else "❌",
                        "EX": "✅" if q_ex else "❌",
                        "Predicted SQL": q_pred[:50],
                        "Gold SQL": q_gold[:50],
                        "Latency (ms)": q_lat,
                    })
                st.dataframe(pd.DataFrame(drill_rows), use_container_width=True)

        # Download / export reports
        st.markdown("### 📥 Download Reports")
        try:
            md_report = generate_markdown_report(displayed_summaries, displayed_results)
            st.download_button("⬇ Download Markdown Report", md_report, "evaluation_report.md", "text/markdown")
            html_report = generate_html_report(displayed_summaries, displayed_results)
            st.download_button("⬇ Download HTML Report", html_report, "evaluation_report.html", "text/html")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: Schema Explorer
# ══════════════════════════════════════════════════════════════════════════════
with main_tabs[3]:
    st.subheader("🗂️ Database Schema Explorer")

    if selected_db_path:
        inspector = load_inspector(selected_db_path)

        schema_col1, schema_col2 = st.columns([1, 2])

        with schema_col1:
            st.markdown("**Tables**")
            selected_table = st.radio("Select a table:", inspector.get_table_names(), key="schema_table")

        with schema_col2:
            if selected_table:
                table = inspector.tables[selected_table]
                st.markdown(f"### `{selected_table}`")
                col_data = [{
                    "Column": c.name,
                    "Type": c.data_type,
                    "PK": "🔑" if c.is_primary_key else "",
                    "Nullable": "✅" if c.is_nullable else "❌",
                    "Sample Values": str(c.sample_values[:3]) if c.sample_values else "—",
                } for c in table.columns]
                st.dataframe(pd.DataFrame(col_data), use_container_width=True)

                if table.foreign_keys:
                    st.markdown("**Foreign Keys & Relationships**")
                    fk_data = [{
                        "From Column": fk.from_column,
                        "→ Target Table": fk.to_table,
                        "→ Target Column": fk.to_column,
                    } for fk in table.foreign_keys]
                    st.dataframe(pd.DataFrame(fk_data), use_container_width=True)

                if table.sample_rows:
                    st.markdown("**Sample Data (top 3 rows)**")
                    st.dataframe(pd.DataFrame(table.sample_rows), use_container_width=True)

        st.divider()
        st.markdown("**Full DDL Schema**")
        st.code(inspector.to_ddl_string(), language="sql")
    else:
        st.info("Please select a database in the sidebar.")
