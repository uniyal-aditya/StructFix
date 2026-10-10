"""Main executable entrypoint for python -m structfix."""

from __future__ import annotations

import argparse
import sys

from structfix.cli import main as cli_main
from structfix.web import create_app


def main() -> int:
    """Entry point dispatching between Web UI server and CLI harness."""
    # Check if CLI repair arguments are provided
    cli_flags = {"-i", "--input", "-s", "--schema", "--cli"}
    args = sys.argv[1:]

    if any(flag in args for flag in cli_flags):
        return cli_main()

    # Web server mode
    parser = argparse.ArgumentParser(
        prog="structfix",
        description="StructFix: Local-First LLM JSON Repair Web Application & CLI",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address to bind the web server to (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000).",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in CLI mode instead of web server.",
    )
    parsed = parser.parse_args(args)

    print("=" * 70)
    print("  StructFix — Local-First LLM JSON Repair Platform")
    print("  Tagline: Generate. Validate. Repair. Trust.")
    print("=" * 70)
    print(f"  Web UI running locally at: http://{parsed.host}:{parsed.port}")
    print("  Deterministic Tier 1 active | Local Ollama Tier 2 ready")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 70)

    app = create_app()
    app.run(host=parsed.host, port=parsed.port, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
