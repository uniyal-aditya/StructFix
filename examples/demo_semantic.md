# Tier 2 Semantic AI Repair Demo

Demonstrates bounded AI repair when LLM output violates JSON schema structure or has prose-wrapped content missing JSON format.

In this scenario, `tests/fixtures/missing_age.json` contains unstructured candidate notes. The target schema requires both `name` and the **MISSING REQUIRED field** `age`.

## Command
```bash
python -m structfix --input tests/fixtures/missing_age.json --schema tests/fixtures/schema.json --model qwen3:1.7b --verbose
```

## Input (`tests/fixtures/missing_age.json`)
```text
Profile Analysis:
Candidate: Fiona Gallagher
Age: 38 years old
Position: Senior SRE
Key Skills: AWS, Go, Prometheus
Active status: true
```

## How StructFix Repairs It
1. **Tier 1** attempts deterministic parse and discovers raw text does not parse to valid JSON object.
2. **Tier 2** engages the local open-weight model (`qwen3:1.7b` via Ollama) with the JSON Schema passed to the `format` parameter.
3. The model extracts the fields semantically, recovering the required `age: 38` and `name: Fiona Gallagher`.
4. Output is validated against the schema and emitted to stdout.

## Expected Output (stdout)
```json
{
  "name": "Fiona Gallagher",
  "age": 38,
  "role": "Senior SRE",
  "skills": [
    "AWS",
    "Go",
    "Prometheus"
  ],
  "active": true
}
```

## Exit Code
`0` (Successful repair)
