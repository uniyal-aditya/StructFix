"""Tier 2 Semantic AI Repair Loop using local Ollama models."""

from __future__ import annotations

import logging
from typing import Any

from structfix.repair.client import OllamaClient
from structfix.repair.parser import coerce_types, parse_and_repair_json
from structfix.repair.prompts import SYSTEM_PROMPT, build_repair_prompt
from structfix.repair.validator import find_missing_required_fields, validate

logger = logging.getLogger("structfix")


def repair_with_ai(
    raw_text: str,
    schema: dict[str, Any],
    client: OllamaClient | None = None,
    model: str = "qwen3:1.7b",
    max_retries: int = 3,
    initial_errors: list[str] | None = None,
) -> tuple[Any, bool, list[str], int, list[str], list[str]]:
    """Execute bounded Tier 2 AI repair loop.

    Args:
        raw_text: Original or partially repaired text.
        schema: Target JSON Schema.
        client: OllamaClient instance (creates default if None).
        model: Model name to use (default: "qwen3:1.7b").
        max_retries: Maximum number of AI repair attempts (capped at 3).
        initial_errors: Known validation errors from previous stage.

    Returns:
        tuple of (
            repaired_data: Any,
            is_valid: bool,
            strategies: list[str],
            ai_calls: int,
            errors: list[str],
            unrecoverable_fields: list[str]
        )
    """
    if client is None:
        client = OllamaClient()

    # Hard cap at max 3 retries
    retries_limit = min(max(1, max_retries), 3)

    current_text = raw_text
    current_errors = initial_errors or ["Failed initial Tier 1 parsing or validation"]
    strategies: list[str] = []
    ai_calls = 0
    last_parsed_data: Any = None

    for attempt in range(1, retries_limit + 1):
        ai_calls += 1
        strategies.append(f"tier2_ai_attempt_{attempt}:{model}")
        logger.debug(f"Starting AI repair attempt {attempt}/{retries_limit} using model {model}")

        prompt = build_repair_prompt(
            original_output=current_text,
            schema=schema,
            validation_errors=current_errors,
            attempt=attempt,
        )

        try:
            raw_response = client.generate(
                prompt=prompt,
                model=model,
                schema=schema,
                system=SYSTEM_PROMPT,
            )
        except Exception as e:
            logger.warning(f"AI call failed on attempt {attempt}: {e}")
            current_errors = [f"Ollama API error: {e}"]
            break

        # Parse AI response using Tier 1 pipeline
        try:
            parsed_data, parse_strats = parse_and_repair_json(raw_response)
            strategies.extend(parse_strats)
            coerced_data, coerce_strats = coerce_types(parsed_data, schema)
            strategies.extend(coerce_strats)
            last_parsed_data = coerced_data
        except Exception as e:
            current_errors = [f"Unparseable AI output: {e}"]
            current_text = raw_response
            continue

        # Validate against schema
        ok, errors = validate(last_parsed_data, schema)
        if ok:
            # Check for unrecoverable fields (required fields explicitly set to null)
            unrecoverable = find_missing_required_fields(last_parsed_data, schema)
            return last_parsed_data, True, strategies, ai_calls, [], unrecoverable

        current_errors = errors
        current_text = raw_response

    # If retries exhausted or broke
    unrecoverable = find_missing_required_fields(last_parsed_data, schema) if last_parsed_data else []
    return last_parsed_data, False, strategies, ai_calls, current_errors, unrecoverable
