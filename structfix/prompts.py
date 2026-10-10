"""Repair prompt templates for StructFix Tier 2 AI Repair."""

from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """You are StructFix AI Repair, a deterministic JSON repair engine.
Your goal is to repair malformed or non-conforming JSON so that it strictly validates against the provided JSON Schema.

CRITICAL CONSTRAINTS:
1. Output ONLY valid JSON adhering strictly to the provided JSON Schema.
2. NEVER invent, hallucinate, or fabricate values.
3. If a required field cannot be recovered or inferred directly from the original output, you MUST set its value to null.
4. Correct syntax errors, structural nesting, key alignment, and data types. Preserve all recoverable original information.
5. Do not output markdown fences, conversational prose, or thinking blocks.
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

--- CURRENT VALIDATION ERRORS ---
{errors_str}
--- END VALIDATION ERRORS ---

INSTRUCTIONS:
1. Fix all validation errors and structural flaws.
2. Ensure the output strictly conforms to the JSON Schema.
3. RULE: Do not invent values. Use null if a value cannot be recovered from the supplied output.
4. Preserve all recoverable original information from the source text.
5. Return ONLY the repaired JSON object or array.
"""
