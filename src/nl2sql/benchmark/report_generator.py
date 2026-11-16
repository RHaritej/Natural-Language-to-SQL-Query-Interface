"""Evaluation Report Generator — produces HTML, Markdown, and JSON reports with comparison tables."""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from .evaluator import StrategySummary, EvaluationItemResult


def generate_markdown_report(
    summaries: List[StrategySummary],
    all_results: Dict[str, List[EvaluationItemResult]],
    output_path: Optional[Path] = None,
) -> str:
    """Generate a comprehensive markdown evaluation report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Natural Language to SQL — Evaluation Report",
        f"**Generated:** {now}\n",
        "---",
        "",
        "## 1. Strategy Comparison Summary",
        "",
        "| Strategy | Total Qs | Exact-Match (EM) | Execution Acc (EX) | Avg Corrections | Avg Latency (ms) |",
        "|----------|----------|------------------|--------------------|-----------------|-----------------|",
    ]

    for s in summaries:
        lines.append(
            f"| {s.strategy:<20} | {s.total_questions:>8} | "
            f"{s.exact_match_count}/{s.total_questions} ({s.exact_match_accuracy_pct:.1f}%) | "
            f"{s.execution_match_count}/{s.total_questions} ({s.execution_accuracy_pct:.1f}%) | "
            f"{s.avg_correction_iterations:.2f} | "
            f"{s.avg_latency_ms:.1f} |"
        )

    lines += ["", "---", "", "## 2. Difficulty Breakdown", ""]

    for s in summaries:
        if not s.difficulty_breakdown:
            continue
        lines.append(f"### Strategy: {s.strategy}")
        lines.append("| Difficulty | Count | Exact-Match | Execution Acc |")
        lines.append("|------------|-------|-------------|---------------|")
        for diff, stats in s.difficulty_breakdown.items():
            lines.append(
                f"| {diff:<12} | {int(stats['count']):>5} | "
                f"{stats['em_accuracy']:.1f}% | "
                f"{stats['ex_accuracy']:.1f}% |"
            )
        lines.append("")

    lines += ["---", "", "## 3. Database Breakdown", ""]

    for s in summaries:
        if not s.database_breakdown:
            continue
        lines.append(f"### Strategy: {s.strategy}")
        lines.append("| Database | Count | Exact-Match | Execution Acc |")
        lines.append("|----------|-------|-------------|---------------|")
        for db_name, stats in s.database_breakdown.items():
            lines.append(
                f"| {db_name:<30} | {int(stats['count']):>5} | "
                f"{stats['em_accuracy']:.1f}% | "
                f"{stats['ex_accuracy']:.1f}% |"
            )
        lines.append("")

    lines += ["---", "", "## 4. Per-Question Details (Failures & Corrections)", ""]

    for strategy, results in all_results.items():
        failures = [r for r in results if not r.execution_accuracy]
        if not failures:
            lines.append(f"### {strategy} — No Failures! All queries executed with 100% accuracy ✅")
            lines.append("")
            continue

        lines.append(f"### {strategy} — Failures ({len(failures)})")
        lines.append("")
        for r in failures[:20]:  # Limit to first 20 failures
            lines.append(f"**Q{r.question_id}** [{r.difficulty}] [{r.db_id}] *{r.question}*")
            lines.append(f"- **Gold:** `{r.gold_sql}`")
            lines.append(f"- **Pred:** `{r.pred_sql or 'NO QUERY GENERATED'}`")
            if r.error_message:
                lines.append(f"- **Error:** {r.error_message}")
            lines.append("")

    lines += ["---", "", "## 5. Metric Definitions", ""]
    lines.append(
        "- **Exact-Match (EM):** Predicted SQL matches gold SQL after AST normalization "
        "(case-insensitive, whitespace-invariant, alias-normalized via `sqlglot`)."
    )
    lines.append(
        "- **Execution Accuracy (EX):** Both queries execute without error and return the same set of rows."
    )
    lines.append(
        "- **Avg Correction Iterations:** Mean number of LLM generation/correction passes per question. "
        "Single-pass strategies show 1.00; self-correction shows ≥1.00."
    )
    lines.append(
        "- **Avg Latency:** Wall-clock time per question in milliseconds including LLM calls, query planning, and execution."
    )
    lines.append("")

    report_text = "\n".join(lines)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_text, encoding="utf-8")

    return report_text


def generate_json_report(
    summaries: List[StrategySummary],
    all_results: Dict[str, List[EvaluationItemResult]],
    output_path: Optional[Path] = None,
) -> dict:
    """Generate structured JSON evaluation report."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "summaries": [s.model_dump() for s in summaries],
        "per_strategy_results": {
            strategy: [r.model_dump() for r in results]
            for strategy, results in all_results.items()
        },
    }

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def generate_html_report(
    summaries: List[StrategySummary],
    all_results: Dict[str, List[EvaluationItemResult]],
    output_path: Optional[Path] = None,
) -> str:
    """Generate a styled HTML evaluation report."""
    rows_html = ""
    for s in summaries:
        rows_html += f"""
        <tr>
            <td><strong>{s.strategy}</strong></td>
            <td>{s.total_questions}</td>
            <td>{s.exact_match_count} / {s.total_questions}<br><span class="pct">{s.exact_match_accuracy_pct:.1f}%</span></td>
            <td>{s.execution_match_count} / {s.total_questions}<br><span class="pct">{s.execution_accuracy_pct:.1f}%</span></td>
            <td>{s.avg_correction_iterations:.2f}</td>
            <td>{s.avg_latency_ms:.1f} ms</td>
        </tr>"""

    diff_html = ""
    for s in summaries:
        if s.difficulty_breakdown:
            diff_html += f"<h3>Strategy: {s.strategy}</h3><table><thead><tr><th>Difficulty</th><th>Count</th><th>Exact-Match</th><th>Execution Acc</th></tr></thead><tbody>"
            for diff, stats in s.difficulty_breakdown.items():
                diff_html += f"<tr><td>{diff}</td><td>{int(stats['count'])}</td><td>{stats['em_accuracy']:.1f}%</td><td>{stats['ex_accuracy']:.1f}%</td></tr>"
            diff_html += "</tbody></table>"

    db_html = ""
    for s in summaries:
        if s.database_breakdown:
            db_html += f"<h3>Strategy: {s.strategy}</h3><table><thead><tr><th>Database</th><th>Count</th><th>Exact-Match</th><th>Execution Acc</th></tr></thead><tbody>"
            for db, stats in s.database_breakdown.items():
                db_html += f"<tr><td>{db}</td><td>{int(stats['count'])}</td><td>{stats['em_accuracy']:.1f}%</td><td>{stats['ex_accuracy']:.1f}%</td></tr>"
            db_html += "</tbody></table>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NL-to-SQL Evaluation Report</title>
<style>
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 1100px; margin: 40px auto; padding: 0 20px; color: #1a1a2e; background: #f8f9fa; }}
  h1 {{ color: #2d6a4f; border-bottom: 3px solid #52b788; padding-bottom: 10px; }}
  h2 {{ color: #40916c; margin-top: 2rem; }}
  h3 {{ color: #52b788; margin-top: 1.5rem; }}
  table {{ border-collapse: collapse; width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,.08); margin-bottom: 2rem; }}
  thead {{ background: #2d6a4f; color: white; }}
  th {{ padding: 14px 16px; text-align: left; font-weight: 600; }}
  td {{ padding: 12px 16px; border-bottom: 1px solid #e9ecef; vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover {{ background: #f0fdf4; }}
  .pct {{ font-size: 0.85rem; color: #2d6a4f; font-weight: 600; }}
  .generated {{ font-size: 0.85rem; color: #6c757d; margin-bottom: 2rem; }}
  .metric-card {{ background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,.08); margin-bottom: 1rem; }}
  code {{ background: #f1f3f5; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; }}
</style>
</head>
<body>
<h1>Natural Language → SQL Evaluation Report</h1>
<p class="generated">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

<h2>1. Strategy Comparison Summary</h2>
<table>
  <thead>
    <tr>
      <th>Strategy</th>
      <th>Questions</th>
      <th>Exact-Match (EM)</th>
      <th>Execution Accuracy (EX)</th>
      <th>Avg Corrections</th>
      <th>Avg Latency</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>

<h2>2. Difficulty Breakdown</h2>
{diff_html}

<h2>3. Database Breakdown</h2>
{db_html}

<h2>4. Metric Definitions</h2>
<div class="metric-card">
  <p><strong>Exact-Match (EM):</strong> Predicted SQL matches gold SQL after AST normalization (case-insensitive, alias-normalized via sqlglot).</p>
  <p><strong>Execution Accuracy (EX):</strong> Both queries execute without error and return the same set of rows.</p>
  <p><strong>Avg Correction Iterations:</strong> Mean generation/correction passes per question. Self-correction shows &ge; 1.00.</p>
  <p><strong>Avg Latency:</strong> Wall-clock time per question including LLM calls, planning, and execution.</p>
</div>
</body>
</html>"""

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

    return html
