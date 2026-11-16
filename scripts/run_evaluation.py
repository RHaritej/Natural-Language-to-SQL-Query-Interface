"""CLI for running NL-to-SQL evaluation across all strategies."""

import sys
import json
import argparse
from pathlib import Path

# Resolve project src directory
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nl2sql.config import QUESTIONS_FILE, DATABASES_DIR, RESULTS_DIR
from nl2sql.benchmark.evaluator import BenchmarkEvaluator
from nl2sql.benchmark.report_generator import generate_markdown_report, generate_json_report, generate_html_report
from nl2sql.llm import get_llm_client
from nl2sql.config import SystemConfig


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate NL-to-SQL strategies on the 100-question benchmark.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Strategies:
  zero_shot       Zero-shot schema-aware prompting
  few_shot        Few-shot exemplar prompting
  cot_planner     Chain-of-Thought with query planning
  self_correction Zero-shot + iterative self-correction
  react_agent     Autonomous ReAct agent with database tools
  all             Run all 5 strategies (default)

Examples:
  python scripts/run_evaluation.py
  python scripts/run_evaluation.py --strategy cot_planner --limit 20
  python scripts/run_evaluation.py --provider mock --strategy all
  python scripts/run_evaluation.py --provider ollama --model llama3.2:latest
  python scripts/run_evaluation.py --strategy all --output-dir evaluation_results/
""",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="all",
        choices=["zero_shot", "few_shot", "cot_planner", "self_correction", "react_agent", "all"],
        help="Strategy to evaluate (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of questions to evaluate (default: all 100)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="mock",
        help="LLM provider: mock, ollama, openai, gemini (default: mock)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="mock-deterministic",
        help="Model name for the provider (default: mock-deterministic or llama3.2:latest for ollama)",
    )
    parser.add_argument(
        "--output-dir",
        "--output",
        dest="output_dir",
        type=str,
        default=None,
        help="Output directory for reports (default: evaluation_results/)",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="all",
        choices=["markdown", "json", "html", "all"],
        help="Report format (default: all)",
    )
    return parser.parse_args()


def run_evaluation():
    args = parse_args()

    # Setup config
    model_name = args.model
    if args.provider == "ollama" and model_name == "mock-deterministic":
        model_name = "llama3.2:latest"

    config = SystemConfig(
        provider=args.provider,
        ollama_model=model_name if args.provider == "ollama" else "llama3.2:latest",
        openai_model=model_name if args.provider == "openai" else "gpt-4o-mini",
        gemini_model=model_name if args.provider == "gemini" else "gemini-1.5-flash",
    )
    llm = get_llm_client(config)

    output_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Verify benchmark data exists
    if not QUESTIONS_FILE.exists():
        print("[WARN] Benchmark questions not found. Running setup first...")
        from scripts.setup_benchmark import setup_benchmark
        setup_benchmark()

    evaluator = BenchmarkEvaluator(
        questions_path=QUESTIONS_FILE,
        databases_dir=DATABASES_DIR,
        llm=llm,
    )

    strategies = (
        ["zero_shot", "few_shot", "cot_planner", "self_correction", "react_agent"]
        if args.strategy == "all"
        else [args.strategy]
    )

    all_summaries = []
    all_results = {}

    for strategy in strategies:
        print(f"\n{'='*60}")
        print(f"[EVAL] Evaluating Strategy: {strategy.upper()} (Provider: {args.provider})")
        print(f"{'='*60}")

        def progress_cb(idx, total, item):
            em = "[PASS]" if item.exact_match else "[FAIL]"
            ex = "[PASS]" if item.execution_accuracy else "[FAIL]"
            print(f"  [{idx:3d}/{total}] Q{item.question_id:3d} EM:{em} EX:{ex}  ({item.latency_ms:.0f}ms)  {item.question[:55]}")

        summary, results = evaluator.evaluate_strategy(
            strategy=strategy,
            limit=args.limit,
            progress_callback=progress_cb,
        )
        all_summaries.append(summary)
        all_results[strategy] = results

        print(f"\n[RESULTS] {strategy} Results:")
        print(f"   Exact-Match Accuracy : {summary.exact_match_accuracy_pct:.1f}%  ({summary.exact_match_count}/{summary.total_questions})")
        print(f"   Execution Accuracy   : {summary.execution_accuracy_pct:.1f}%  ({summary.execution_match_count}/{summary.total_questions})")
        print(f"   Avg Corrections      : {summary.avg_correction_iterations:.2f}")
        print(f"   Avg Latency          : {summary.avg_latency_ms:.1f} ms")

    # Print final comparison table
    print(f"\n{'='*80}")
    print("FINAL COMPARISON TABLE")
    print(f"{'='*80}")
    print(f"{'Strategy':<22} {'EM%':>8} {'EX%':>8} {'Avg Iter':>10} {'Avg Latency':>14}")
    print(f"{'-'*22} {'-'*8} {'-'*8} {'-'*10} {'-'*14}")
    for s in all_summaries:
        print(
            f"{s.strategy:<22} {s.exact_match_accuracy_pct:>7.1f}% {s.execution_accuracy_pct:>7.1f}%"
            f" {s.avg_correction_iterations:>10.2f} {s.avg_latency_ms:>12.1f}ms"
        )

    # Generate reports
    report_format = args.format

    if report_format in ("markdown", "all"):
        md_path = output_dir / "evaluation_report.md"
        generate_markdown_report(all_summaries, all_results, md_path)
        print(f"\n[REPORT] Markdown report: {md_path}")

    if report_format in ("json", "all"):
        json_path = output_dir / "evaluation_results.json"
        generate_json_report(all_summaries, all_results, json_path)
        print(f"[REPORT] JSON results:    {json_path}")

    if report_format in ("html", "all"):
        html_path = output_dir / "evaluation_report.html"
        generate_html_report(all_summaries, all_results, html_path)
        print(f"[REPORT] HTML report:     {html_path}")

    print("\n[PASS] Evaluation complete!")


if __name__ == "__main__":
    run_evaluation()
