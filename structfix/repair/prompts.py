"""Repair prompt templates for StructFix Tier 2 AI Repair."""

from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """You are StructFix AI Repair, a deterministic JSON repair assistant.
Your task is to repair malformed or non-conforming JSON to strictly validate against the provided JSON Schema.

CRITICAL RULES:
1. Output ONLY valid JSON adhering strictly to the provided JSON Schema.
2. NEVER invent, hallucinate, or fabricate values.
3. If a required field cannot be recovered or inferred directly from the original output, you MUST set its value to null.
4. Correct syntax errors, extract values, fix structural nesting, and align data types.
5. Do not include markdown fences, prose, or conversational commentary.
"""


def build_repair_prompt(
    original_output: str,
    schema: dict[str, Any],
    validation_errors: list[str],
    attempt: int = 1,
) -> str:
    """Build a structured repair prompt for Ollama."""
    schema_str = json.dumps(schema, indent=2)
    errors_str = "\n".join(f"- {err}" for err in validation_errors) if validation_errors else "None"

    return f"""[ATTEMPT {attempt}]
The following LLM output is malformed or failed JSON Schema validation:

--- ORIGINAL MALFORMED OUTPUT ---
{original_output}
--- END ORIGINAL OUTPUT ---

--- TARGET JSON SCHEMA ---
{schema_str}
--- END JSON SCHEMA ---

--- VALIDATION ERRORS ---
{errors_str}
--- END VALIDATION ERRORS ---

INSTRUCTIONS:
1. Fix all validation errors and structural flaws.
2. Ensure the output strictly conforms to the JSON Schema.
3. RULE: Do not invent values; use null if unknown or if the value is absent in the original text.
4. Return ONLY the repaired JSON object or array.
"""
