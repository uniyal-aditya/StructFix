"""Flask Web Application for StructFix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from flask import Flask, jsonify, render_template, request

from structfix.engine import repair
from structfix.logging_config import setup_logger
from structfix.models.client import OllamaClient
from structfix.repair.validator import validate_schema

logger = setup_logger("structfix.web")

# Resolve templates and static directories relative to package
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
FIXTURES_DIR = BASE_DIR.parent / "tests" / "fixtures"


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask web application."""
    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR),
        static_folder=str(STATIC_DIR),
    )

    # 2MB request payload size limit for safety
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

    if test_config:
        app.config.update(test_config)

    @app.route("/", methods=["GET"])
    def index():
        """Render main interactive user interface."""
        return render_template("index.html")

    @app.route("/api/health", methods=["GET"])
    def health():
        """Check server health and Ollama model connectivity."""
        client = OllamaClient()
        ollama_status = client.check_health()
        ollama_status["configured_model"] = "qwen3:1.7b"

        return jsonify({
            "status": "ok",
            "version": "0.1.0",
            "ollama": ollama_status,
            "engine": "local-first hybrid",
        })

    @app.route("/api/examples", methods=["GET"])
    def examples():
        """Return available demonstration fixtures and schemas."""
        fixtures = []
        schema_path = FIXTURES_DIR / "schema.json"
        default_schema = {}
        if schema_path.exists():
            try:
                default_schema = json.loads(schema_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        example_meta = [
            {
                "id": "valid",
                "title": "Valid JSON",
                "category": "Baseline",
                "description": "Pristine JSON that already satisfies the schema (Tier 0).",
                "file": "valid.json",
                "expected_tier": 0,
            },
            {
                "id": "fenced",
                "title": "Markdown Fences & <think> Tags",
                "category": "Deterministic",
                "description": "LLM output wrapped in code fences with reasoning tokens.",
                "file": "fenced.json",
                "expected_tier": 1,
            },
            {
                "id": "trailing_comma",
                "title": "Trailing Commas",
                "category": "Deterministic",
                "description": "JSON containing illegal trailing commas in objects and arrays.",
                "file": "trailing_comma.json",
                "expected_tier": 1,
            },
            {
                "id": "single_quotes",
                "title": "Single Quotes",
                "category": "Deterministic",
                "description": "JSON keys and strings improperly enclosed in single quotes.",
                "file": "single_quotes.json",
                "expected_tier": 1,
            },
            {
                "id": "wrong_type",
                "title": "String Numbers (Type Coercion)",
                "category": "Deterministic",
                "description": "Numbers and booleans represented as strings requiring safe schema coercion.",
                "file": "wrong_type.json",
                "expected_tier": 1,
            },
            {
                "id": "missing_age",
                "title": "Missing Required Field (Semantic Recovery)",
                "category": "Semantic AI",
                "description": "Unstructured candidate notes requiring extraction of required age field.",
                "file": "missing_age.json",
                "expected_tier": 2,
            },
            {
                "id": "unrecoverable",
                "title": "Unrecoverable Required Field",
                "category": "Zero-Hallucination",
                "description": "Required age field is omitted completely from text; must return null.",
                "file": "unrecoverable.json",
                "expected_tier": 2,
            },
        ]

        for item in example_meta:
            content = ""
            target_file = FIXTURES_DIR / item["file"]
            if target_file.exists():
                content = target_file.read_text(encoding="utf-8")

            fixtures.append({
                "id": item["id"],
                "title": item["title"],
                "category": item["category"],
                "description": item["description"],
                "input": content,
                "schema": default_schema,
                "expected_tier": item["expected_tier"],
            })

        return jsonify({"examples": fixtures})

    @app.route("/api/repair", methods=["POST"])
    def repair_endpoint():
        """Execute repair on input text with provided schema."""
        if not request.is_json:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        body = request.get_json(silent=True)
        if body is None:
            return jsonify({"error": "Malformed JSON in request payload"}), 400

        raw_input = body.get("input", "")
        if not isinstance(raw_input, str):
            return jsonify({"error": "'input' field must be a string"}), 400

        schema_raw = body.get("schema")
        schema_dict = None

        if schema_raw is not None:
            if isinstance(schema_raw, str):
                trimmed = schema_raw.strip()
                if trimmed:
                    try:
                        schema_dict = json.loads(trimmed)
                    except Exception as e:
                        return jsonify({"error": f"Invalid JSON Schema string: {e}"}), 400
            elif isinstance(schema_raw, dict):
                schema_dict = schema_raw
            else:
                return jsonify({"error": "'schema' must be a JSON object or string"}), 400

        # Validate schema structure itself before running repair
        if schema_dict:
            schema_ok, schema_err = validate_schema(schema_dict)
            if not schema_ok:
                return jsonify({"error": f"Invalid JSON Schema: {schema_err}"}), 400

        model = body.get("model", "qwen3:1.7b")
        if model not in ("qwen3:1.7b", "llama3.2"):
            model = "qwen3:1.7b"

        enable_ai = bool(body.get("enable_ai", True))
        try:
            max_retries = int(body.get("max_retries", 3))
            max_retries = min(max(0, max_retries), 3)
        except (ValueError, TypeError):
            max_retries = 3

        logger.debug(
            f"Received repair request: model={model}, enable_ai={enable_ai}, "
            f"max_retries={max_retries}, input_length={len(raw_input)}"
        )

        result = repair(
            raw_input=raw_input,
            schema=schema_dict,
            model=model,
            max_retries=max_retries,
            enable_tier2=enable_ai,
        )

        return jsonify({
            "status": result.status,
            "is_valid": result.is_valid,
            "tier_used": result.tier_used,
            "attempts": result.attempts,
            "ai_calls": result.ai_calls,
            "latency_ms": round(result.latency_ms, 2),
            "strategies_applied": result.strategies_applied,
            "data": result.data,
            "errors": result.errors,
            "unrecoverable_fields": result.unrecoverable_fields,
        })

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({"error": "Payload exceeds maximum allowed size (2MB)"}), 413

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)
