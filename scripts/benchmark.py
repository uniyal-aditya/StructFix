"""StructFix Benchmark Suite.

Runs all test fixtures across configured models and measures real-time performance:
pass rate, tier resolution, ai calls, and latency.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from structfix.engine import repair
from structfix.repair.client import OllamaClient


def check_ollama_available(base_url: str = "http://localhost:11434") -> bool:
    """Check if local Ollama server is reachable."""
    import requests
    try:
        res = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=2.0)
        return res.status_code == 200
    except Exception:
        return False


def run_benchmarks(
    models: list[str],
    fixtures_dir: Path,
    schema_file: Path,
    tier1_only: bool = False,
    verbose: bool = False,
) -> dict[str, list[dict]]:
    """Run benchmark matrix across all fixtures and models."""
    if not fixtures_dir.exists():
        raise FileNotFoundError(f"Fixtures directory not found: {fixtures_dir}")
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")

    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    fixture_files = sorted(
        [f for f in fixtures_dir.glob("*.json") if f.name != "schema.json"]
    )

    ollama_online = False if tier1_only else check_ollama_available()
    if tier1_only:
        sys.stderr.write("[BENCHMARK] Running in Deterministic Tier 1-Only mode (--tier1-only).\n\n")
    elif not ollama_online:
        sys.stderr.write(
            "[BENCHMARK] Note: Ollama server not detected at localhost:11434. "
            "Tier 2 AI repairs will be tested with fallback/offline behavior.\n\n"
        )

    results_by_model: dict[str, list[dict]] = {}

    target_models = ["Deterministic Tier 1"] if tier1_only else models

    for model in target_models:
        model_results = []
        for fixture_path in fixture_files:
            content = fixture_path.read_text(encoding="utf-8")
            start = time.perf_counter()
            result = repair(
                raw_input=content,
                schema=schema,
                model=model if not tier1_only else "qwen3:1.7b",
                enable_tier2=ollama_online and not tier1_only,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            model_results.append({
                "fixture": fixture_path.name,
                "status": result.status,
                "is_valid": result.is_valid,
                "tier_used": result.tier_used,
                "ai_calls": result.ai_calls,
                "latency_ms": elapsed_ms,
                "strategies": ", ".join(result.strategies_applied) if result.strategies_applied else "none",
                "unrecoverable": ", ".join(result.unrecoverable_fields) if result.unrecoverable_fields else "none",
            })
        results_by_model[model] = model_results

    return results_by_model


def print_report(results_by_model: dict[str, list[dict]]) -> None:
    """Format and print benchmark results as clean tables."""
    print("=" * 88)
    print("                      STRUCTFIX PERFORMANCE BENCHMARK REPORT")
    print("=" * 88)

    for model, runs in results_by_model.items():
        print(f"\nTarget Evaluation: {model}")
        print("-" * 88)
        header = f"{'Fixture':<22} | {'Status':<13} | {'Tier':<5} | {'AI Calls':<8} | {'Latency (ms)':<12} | {'Strategies'}"
        print(header)
        print("-" * 88)

        total_runs = len(runs)
        passed_runs = sum(1 for r in runs if r["is_valid"])
        total_latency = sum(r["latency_ms"] for r in runs)
        tier1_count = sum(1 for r in runs if r["tier_used"] in (0, 1) and r["is_valid"])
        tier2_count = sum(1 for r in runs if r["tier_used"] == 2 and r["is_valid"])

        for r in runs:
            status_display = r["status"].upper()
            row = (
                f"{r['fixture']:<22} | "
                f"{status_display:<13} | "
                f"{str(r['tier_used']):<5} | "
                f"{r['ai_calls']:<8} | "
                f"{r['latency_ms']:<12.2f} | "
                f"{r['strategies'][:30]}"
            )
            print(row)

        print("-" * 88)
        pass_rate = (passed_runs / total_runs) * 100 if total_runs > 0 else 0
        avg_lat = total_latency / total_runs if total_runs > 0 else 0
        print(f"Summary for {model}:")
        print(f"  - Valid / Conforming: {passed_runs}/{total_runs} ({pass_rate:.1f}%)")
        print(f"  - Average Latency: {avg_lat:.2f} ms")
        print(f"  - Deterministic Solves (Tier 0/1): {tier1_count}")
        print(f"  - AI Solves (Tier 2): {tier2_count}")
        print("=" * 88)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run StructFix Benchmarks")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["qwen3:1.7b", "llama3.2"],
        help="Models to benchmark against",
    )
    parser.add_argument(
        "--tier1-only",
        "--deterministic-only",
        action="store_true",
        help="Run benchmarks in Tier 1 deterministic-only mode (no LLM required).",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("tests/fixtures"),
        help="Path to fixtures directory",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("tests/fixtures/schema.json"),
        help="Path to schema file",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    args = parser.parse_args()

    results = run_benchmarks(
        models=args.models,
        fixtures_dir=args.fixtures,
        schema_file=args.schema,
        tier1_only=args.tier1_only,
        verbose=args.verbose,
    )
    print_report(results)


if __name__ == "__main__":
    main()
