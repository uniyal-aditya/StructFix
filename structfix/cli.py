"""Command Line Interface for StructFix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from structfix.engine import repair
from structfix.logger import setup_logger


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="structfix",
        description="StructFix: Lightweight, local-first harness to repair malformed LLM JSON output.",
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Path to the file containing malformed JSON / LLM output (use '-' for stdin).",
    )
    parser.add_argument(
        "-s",
        "--schema",
        required=False,
        default=None,
        help="Path to the JSON Schema file to validate and guide repairs.",
    )
    parser.add_argument(
        "-m",
        "--model",
        default="qwen3:1.7b",
        help="Ollama model name for Tier 2 AI repair (default: 'qwen3:1.7b').",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum AI retry attempts (default: 3, max: 3).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging to stderr.",
    )
    parser.add_argument(
        "--no-tier2",
        action="store_true",
        help="Disable Tier 2 AI repair and use Tier 1 deterministic repair only.",
    )
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Entrypoint for StructFix CLI."""
    try:
        parsed_args = parse_args(args)
    except SystemExit as e:
        return 2 if e.code != 0 else 0

    logger = setup_logger(verbose=parsed_args.verbose)

    # Read input file
    input_text = ""
    if parsed_args.input == "-":
        input_text = sys.stdin.read()
    else:
        input_path = Path(parsed_args.input)
        if not input_path.exists() or not input_path.is_file():
            sys.stderr.write(f"Error: Input file not found: {parsed_args.input}\n")
            return 2
        try:
            input_text = input_path.read_text(encoding="utf-8")
        except Exception as e:
            sys.stderr.write(f"Error reading input file {parsed_args.input}: {e}\n")
            return 2

    # Read schema file if provided
    schema_dict = None
    if parsed_args.schema:
        schema_path = Path(parsed_args.schema)
        if not schema_path.exists() or not schema_path.is_file():
            sys.stderr.write(f"Error: Schema file not found: {parsed_args.schema}\n")
            return 2
        try:
            schema_dict = json.loads(schema_path.read_text(encoding="utf-8"))
        except Exception as e:
            sys.stderr.write(f"Error parsing schema JSON {parsed_args.schema}: {e}\n")
            return 2

    logger.debug(f"Loaded input ({len(input_text)} chars) and schema.")

    # Execute repair
    result = repair(
        raw_input=input_text,
        schema=schema_dict,
        model=parsed_args.model,
        max_retries=parsed_args.max_retries,
        enable_tier2=not parsed_args.no_tier2,
    )

    logger.debug(
        f"Repair completed in {result.latency_ms:.2f}ms | status: {result.status} | "
        f"tier: {result.tier_used} | ai_calls: {result.ai_calls} | "
        f"strategies: {result.strategies_applied}"
    )

    if result.unrecoverable_fields:
        sys.stderr.write(
            f"[WARNING] Unrecoverable fields set to null: {', '.join(result.unrecoverable_fields)}\n"
        )

    if result.is_valid and result.data is not None:
        # Output clean valid JSON to stdout
        sys.stdout.write(json.dumps(result.data, indent=2) + "\n")
        return 0
    else:
        sys.stderr.write("StructFix Error: Failed to repair JSON.\n")
        for err in result.errors:
            sys.stderr.write(f"  - {err}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
