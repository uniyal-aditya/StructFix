---
name: structfix
description: Repair malformed, syntax-broken, or schema-violating LLM JSON outputs using fast deterministic rules (Tier 1) and bounded local AI model repair (Tier 2 via Ollama).
---

# StructFix Agent Skill

Use **StructFix** when an LLM returns malformed JSON, markdown-wrapped data, single-quoted strings, trailing commas, or output that fails JSON Schema validation.

## Quick CLI Usage

```bash
# Repair broken JSON against a target schema
python -m structfix --input path/to/broken_output.json --schema path/to/schema.json

# Repair with specific local model (default: qwen3:1.7b, alt: llama3.2)
python -m structfix --input path/to/broken_output.json --schema path/to/schema.json --model qwen3:1.7b --verbose

# Run deterministic repairs only (instant, no Ollama needed)
python -m structfix --input path/to/broken_output.json --schema path/to/schema.json --no-tier2
```

## Python API Usage

```python
from structfix import repair

raw_output = "```json\n{'name': 'Alice', 'age': '30',}\n```"
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"}
    },
    "required": ["name", "age"]
}

result = repair(raw_output, schema=schema)
if result.is_valid:
    print("Repaired data:", result.data)
    print("Strategies applied:", result.strategies_applied)
    print(f"Latency: {result.latency_ms:.2f}ms | Tier used: {result.tier_used}")
else:
    print("Repair failed with errors:", result.errors)
```

## How StructFix Operates

1. **Tier 1 (Deterministic)**:
   - Strips `<think>` tags and ```json markdown fences.
   - Extracts JSON objects/arrays from conversational prose.
   - Fixes single quotes and trailing commas.
   - Coerces safe types (string-to-int, string-to-float, booleans).
2. **Tier 2 (Bounded AI Fallback)**:
   - Feeds broken output, schema, and exact JSONPath errors to a local open-weight model (`qwen3:1.7b`).
   - Uses schema-constrained decoding (`format` parameter).
   - Retries up to 3 times.
   - **Zero Hallucination Policy**: If a required field cannot be determined, it sets it to `null` and marks it as unrecoverable.

## Exit Codes

- `0`: Valid JSON produced (printed directly to `stdout`).
- `1`: Unrepairable (errors printed to `stderr`).
- `2`: CLI usage / argument error.
