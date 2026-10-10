"""Core Orchestrator Engine for StructFix."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from structfix.models.result import RepairResult
from structfix.repair.ai_repair import repair_with_ai
from structfix.repair.client import OllamaClient
from structfix.repair.parser import coerce_types, parse_and_repair_json
from structfix.repair.validator import find_missing_required_fields, validate

logger = logging.getLogger("structfix")


def repair(
    raw_input: str,
    schema: dict[str, Any] | None = None,
    model: str = "qwen3:1.7b",
    max_retries: int = 3,
    client: OllamaClient | None = None,
    enable_tier2: bool = True,
) -> RepairResult:
    """Repair malformed JSON output using Tier 1 deterministic fixes and Tier 2 AI fallback.

    Args:
        raw_input: Broken or raw string containing JSON.
        schema: Optional JSON Schema dict to validate against and guide repairs.
        model: Small open-weight model name for Tier 2 repair (default: "qwen3:1.7b").
        max_retries: Maximum AI retry cycles (capped at 3).
        client: Optional OllamaClient instance.
        enable_tier2: Whether to engage Tier 2 AI repair when Tier 1 is insufficient.

    Returns:
        RepairResult with status, tier used, execution latency, and repaired data.
    """
    start_time = time.perf_counter()
    strategies: list[str] = []

    # Step 0: Fast path - check if raw input is already pristine valid JSON
    try:
        pristine_data = json.loads(raw_input.strip())
        ok, errors = validate(pristine_data, schema)
        if ok:
            unrec = find_missing_required_fields(pristine_data, schema)
            latency = (time.perf_counter() - start_time) * 1000
            status = "unrecoverable" if unrec else "success"
            logger.debug("Input is already valid JSON meeting schema.")
            return RepairResult(
                status=status,
                tier_used=0,
                attempts=0,
                ai_calls=0,
                latency_ms=latency,
                strategies_applied=["pristine_valid"],
                data=pristine_data,
                errors=[],
                unrecoverable_fields=unrec,
            )
    except Exception:
        pass

    # Step 1: Tier 1 Deterministic Repair
    logger.debug("Attempting Tier 1 deterministic repair...")
    tier1_parsed_data: Any = None
    tier1_errors: list[str] = []
    tier1_success = False

    try:
        parsed_data, parse_strats = parse_and_repair_json(raw_input)
        strategies.extend(parse_strats)

        # Apply schema-guided type coercions
        coerced_data, coerce_strats = coerce_types(parsed_data, schema)
        strategies.extend(coerce_strats)
        tier1_parsed_data = coerced_data

        # Validate against schema
        ok, errors = validate(tier1_parsed_data, schema)
        if ok:
            tier1_success = True
            unrec = find_missing_required_fields(tier1_parsed_data, schema)
            latency = (time.perf_counter() - start_time) * 1000
            status = "unrecoverable" if unrec else "success"
            logger.info("Tier 1 deterministic repair succeeded.")
            return RepairResult(
                status=status,
                tier_used=1,
                attempts=1,
                ai_calls=0,
                latency_ms=latency,
                strategies_applied=strategies,
                data=tier1_parsed_data,
                errors=[],
                unrecoverable_fields=unrec,
            )
        else:
            tier1_errors = errors
            logger.debug(f"Tier 1 repaired syntax but schema validation failed: {errors}")
    except Exception as e:
        tier1_errors = [f"Tier 1 parsing failed: {e}"]
        logger.debug(f"Tier 1 parsing failed: {e}")

    # If Tier 1 failed or didn't meet schema, decide on Tier 2
    if not enable_tier2 or not schema:
        latency = (time.perf_counter() - start_time) * 1000
        logger.warning("Repair failed: Tier 1 exhausted and Tier 2 not engaged.")
        return RepairResult(
            status="failed",
            tier_used=1,
            attempts=1,
            ai_calls=0,
            latency_ms=latency,
            strategies_applied=strategies,
            data=tier1_parsed_data,
            errors=tier1_errors,
            unrecoverable_fields=[],
        )

    # Step 2: Tier 2 AI Repair
    logger.info(f"Engaging Tier 2 AI repair with model '{model}'...")
    ai_data, ai_valid, ai_strats, ai_calls, ai_errors, unrec = repair_with_ai(
        raw_text=raw_input,
        schema=schema,
        client=client,
        model=model,
        max_retries=max_retries,
        initial_errors=tier1_errors,
    )
    strategies.extend(ai_strats)
    latency = (time.perf_counter() - start_time) * 1000

    if ai_valid:
        status = "unrecoverable" if unrec else "success"
        logger.info(f"Tier 2 AI repair succeeded after {ai_calls} call(s).")
        return RepairResult(
            status=status,
            tier_used=2,
            attempts=1 + ai_calls,
            ai_calls=ai_calls,
            latency_ms=latency,
            strategies_applied=strategies,
            data=ai_data,
            errors=[],
            unrecoverable_fields=unrec,
        )

    logger.warning(f"Tier 2 AI repair failed after {ai_calls} call(s).")
    return RepairResult(
        status="failed",
        tier_used=2,
        attempts=1 + ai_calls,
        ai_calls=ai_calls,
        latency_ms=latency,
        strategies_applied=strategies,
        data=ai_data,
        errors=ai_errors,
        unrecoverable_fields=unrec,
    )
