# Unrecoverable Required Field Demo (Zero Hallucination Policy)

Demonstrates StructFix's strict zero-hallucination policy. When a required field (`age`) is completely missing from the original output and cannot be inferred, StructFix mandates `null` for that field rather than fabricating values, and reports it as unrecoverable.

## Command
```bash
python -m structfix --input tests/fixtures/unrecoverable.json --schema tests/fixtures/schema.json --model qwen3:1.7b
```

## Input (`tests/fixtures/unrecoverable.json`)
```text
Profile Summary:
Candidate: George Miller
Position: Infrastructure Architect
Competencies: Terraform, Linux, Python
Profile Status: active
Note: Age was not specified in the resume.
```

## How StructFix Handles It
1. Target schema requires both `name` and `age` (`age: ["integer", "null"]`).
2. StructFix instructs the repair model: *"NEVER invent values. If a required field cannot be recovered from the original text, you must return null for it"*.
3. The repair process produces `"age": null` and flags `age` in `unrecoverable_fields`.
4. A warning is written to `stderr` indicating unrecoverable fields.

## Expected Output (stdout)
```json
{
  "name": "George Miller",
  "age": null,
  "role": "Infrastructure Architect",
  "skills": [
    "Terraform",
    "Linux",
    "Python"
  ],
  "active": true
}
```

## Stderr Diagnostic Warning
```text
[WARNING] Unrecoverable fields set to null: age
```

## Exit Code
`0` (Valid JSON conforming to nullable schema)
