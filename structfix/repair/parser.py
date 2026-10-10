"""Tier 1 Deterministic JSON Parser and Repair Module.

Provides fast, rule-based fixes for common LLM JSON formatting issues:
- Stripping <think> reasoning blocks
- Stripping markdown code fences (```json ... ```)
- Extracting JSON from conversational prose
- Fixing single quotes and trailing commas
- Safe type coercion guided by JSON schema
"""

from __future__ import annotations

import json
import re
from typing import Any

import json_repair


def strip_thinking_tags(text: str) -> str:
    """Remove <think>...</think> reasoning blocks from LLM responses."""
    if not text:
        return ""
    # Strip closed <think>...</think> tags
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Strip unclosed <think> tags if model output was cut off
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()


def strip_markdown_fences(text: str) -> str:
    """Extract JSON content from markdown code fences (e.g. ```json ... ```)."""
    if not text:
        return ""
    text = strip_thinking_tags(text).strip()

    # Pattern for ```json ... ``` or ``` ... ```
    fence_pattern = re.compile(r"^```(?:json|JSON)?\s*\n?(.*?)\n?```$", re.DOTALL)
    match = fence_pattern.search(text)
    if match:
        return match.group(1).strip()

    # If code fence is embedded within text
    embedded_fence = re.compile(r"```(?:json|JSON)?\s*\n?(.*?)\n?```", re.DOTALL)
    matches = embedded_fence.findall(text)
    if matches:
        # Return the largest block that looks like JSON
        for candidate in matches:
            cand = candidate.strip()
            if (cand.startswith("{") and cand.endswith("}")) or (
                cand.startswith("[") and cand.endswith("]")
            ):
                return cand
        return matches[0].strip()

    # Remove leading/trailing stray backticks
    if text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    return text.strip()


def extract_json_from_prose(text: str) -> str:
    """Extract JSON object or array substring from conversational prose.

    Handles outputs like "Sure, here is your data: { ... } Hope this helps!"
    """
    if not text:
        return ""
    text = strip_markdown_fences(text)

    # First check if text is already clean JSON
    trimmed = text.strip()
    if (trimmed.startswith("{") and trimmed.endswith("}")) or (
        trimmed.startswith("[") and trimmed.endswith("]")
    ):
        return trimmed

    # Look for opening bracket/brace
    start_brace = trimmed.find("{")
    start_bracket = trimmed.find("[")

    if start_brace == -1 and start_bracket == -1:
        return trimmed

    # Determine which starts first
    if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        start_char = "{"
        end_char = "}"
        start_idx = start_brace
    else:
        start_char = "["
        end_char = "]"
        start_idx = start_bracket

    # Balanced bracket scan
    depth = 0
    in_string = False
    escape = False
    end_idx = -1

    for i in range(start_idx, len(trimmed)):
        char = trimmed[i]
        if escape:
            escape = False
            continue
        if char == "\\" and in_string:
            escape = True
            continue
        if char == '"' or char == "'":
            in_string = not in_string
            continue
        if in_string:
            continue

        if char == start_char:
            depth += 1
        elif char == end_char:
            depth -= 1
            if depth == 0:
                end_idx = i
                break

    if end_idx != -1:
        return trimmed[start_idx : end_idx + 1].strip()

    # Fallback to rfind if balanced bracket scanning failed (e.g. malformed quotes)
    last_end = trimmed.rfind(end_char)
    if last_end != -1 and last_end > start_idx:
        return trimmed[start_idx : last_end + 1].strip()

    return trimmed[start_idx:].strip()


def fix_single_quotes_and_trailing_commas(text: str) -> str:
    """Repair single quotes and trailing commas using heuristics and json-repair."""
    if not text:
        return ""

    cleaned = text.strip()

    # Fast path: try standard json parsing first
    try:
        json.loads(cleaned)
        return cleaned
    except Exception:
        pass

    # Attempt repair using json_repair
    try:
        repaired = json_repair.repair_json(cleaned, return_objects=False)
        if isinstance(repaired, str) and repaired:
            # Verify repaired string is valid JSON
            json.loads(repaired)
            return repaired
    except Exception:
        pass

    return cleaned


def parse_and_repair_json(text: str) -> tuple[Any, list[str]]:
    """Execute full Tier 1 text-level parsing and repair pipeline.

    Returns the parsed Python data structure and a list of applied repair strategies.
    """
    strategies: list[str] = []
    if not text or not text.strip():
        raise ValueError("Empty or whitespace-only input provided.")

    current = text.strip()

    # 1. Thinking tags
    if "<think>" in current:
        current = strip_thinking_tags(current)
        strategies.append("strip_thinking_tags")

    # 2. Markdown fences
    if "```" in current:
        current = strip_markdown_fences(current)
        strategies.append("strip_markdown_fences")

    # 3. Prose extraction
    trimmed = current.strip()
    if not ((trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]"))):
        extracted = extract_json_from_prose(trimmed)
        if extracted != trimmed:
            current = extracted
            strategies.append("extract_json_from_prose")

    # 4. Standard parse attempt
    try:
        data = json.loads(current)
        return data, strategies
    except Exception:
        pass

    # 5. Fix single quotes / trailing commas via json-repair
    try:
        repaired_data = json_repair.repair_json(current, return_objects=True)
        if repaired_data is not None and repaired_data != "":
            strategies.append("json_repair_syntax")
            return repaired_data, strategies
    except Exception:
        pass

    # If all failed, raise ValueError
    raise ValueError(f"Unable to parse JSON after Tier 1 repairs: {current[:100]}...")


def _coerce_value(value: Any, expected_types: list[str]) -> tuple[Any, bool]:
    """Helper to safely coerce a single value to one of the expected JSON types."""
    if value is None:
        return None, False

    # String to number / integer
    if isinstance(value, str):
        val_str = value.strip()

        # Handle null string representations
        if "null" in expected_types and val_str.lower() in ("null", "none", "n/a", ""):
            return None, True

        # Handle boolean strings
        if "boolean" in expected_types:
            if val_str.lower() in ("true", "yes", "1"):
                return True, True
            if val_str.lower() in ("false", "no", "0"):
                return False, True

        # Handle integer
        if "integer" in expected_types:
            try:
                # Check pure int or float that represents whole number (e.g. "30" or "30.0")
                float_val = float(val_str)
                if float_val.is_integer():
                    return int(float_val), True
            except ValueError:
                pass

        # Handle number / float
        if "number" in expected_types:
            try:
                float_val = float(val_str)
                return float_val, True
            except ValueError:
                pass

    # Number to integer coercion if integer expected and is whole number
    if isinstance(value, float) and "integer" in expected_types and value.is_integer():
        return int(value), True

    # Integer to float/number is generally already valid JSON number, but if needed:
    if isinstance(value, int) and "number" in expected_types and "integer" not in expected_types:
        return float(value), False

    return value, False


def coerce_types(data: Any, schema: dict[str, Any] | None) -> tuple[Any, list[str]]:
    """Safely coerce types in data based on a JSON Schema.

    Applies safe conversions such as:
    - "19.99" -> 19.99 (number)
    - "30" -> 30 (integer)
    - "true" -> True (boolean)
    - "null" -> None (null)

    Does not fabricate data or guess ambiguous conversions.
    """
    if schema is None or not isinstance(schema, dict) or data is None:
        return data, []

    strategies: list[str] = []

    def _get_types_from_schema(s: dict[str, Any]) -> list[str]:
        types: list[str] = []
        if "type" in s:
            t = s["type"]
            if isinstance(t, str):
                types.append(t.lower())
            elif isinstance(t, list):
                types.extend([x.lower() for x in t if isinstance(x, str)])
        for key in ("anyOf", "oneOf"):
            if key in s and isinstance(s[key], list):
                for sub in s[key]:
                    if isinstance(sub, dict) and "type" in sub:
                        st = sub["type"]
                        if isinstance(st, str):
                            types.append(st.lower())
                        elif isinstance(st, list):
                            types.extend([x.lower() for x in st if isinstance(x, str)])
        return list(set(types))

    def _traverse(val: Any, sch: dict[str, Any], path: str = "") -> Any:
        if sch is None or not isinstance(sch, dict):
            return val

        expected_types = _get_types_from_schema(sch)

        # If val is a primitive (or str) and expected types are given, attempt coercion
        if expected_types:
            new_val, changed = _coerce_value(val, expected_types)
            if changed:
                strategies.append(f"coerce_type:{path or 'root'}({val!r}->{new_val!r})")
                val = new_val

        # If schema defines an object with properties
        if isinstance(val, dict):
            props = sch.get("properties", {})
            for k, sub_sch in props.items():
                if k in val and isinstance(sub_sch, dict):
                    prop_path = f"{path}.{k}" if path else k
                    val[k] = _traverse(val[k], sub_sch, prop_path)

        # If schema defines an array with items
        elif isinstance(val, list):
            item_sch = sch.get("items")
            if isinstance(item_sch, dict):
                for idx in range(len(val)):
                    item_path = f"{path}[{idx}]"
                    val[idx] = _traverse(val[idx], item_sch, item_path)

        return val

    # Make a copy if dict or list to avoid unexpected in-place mutation issues
    import copy

    coerced_data = _traverse(copy.deepcopy(data), schema)
    return coerced_data, strategies
