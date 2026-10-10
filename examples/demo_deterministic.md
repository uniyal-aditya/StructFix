# Tier 1 Deterministic Repair Demo

Demonstrates instant, zero-cost deterministic repair of syntax errors, markdown fences, single quotes, trailing commas, and string-to-number types.

## 1. Stripping Markdown Fences & Reasoning Tags

### Command
```bash
python -m structfix --input tests/fixtures/fenced.json --schema tests/fixtures/schema.json
```

### Expected Output (stdout)
```json
{
  "name": "Bob Smith",
  "age": 34,
  "role": "Backend Engineer",
  "skills": [
    "rust",
    "postgres"
  ],
  "active": true
}
```

---

## 2. Fixing Trailing Commas

### Command
```bash
python -m structfix --input tests/fixtures/trailing_comma.json --schema tests/fixtures/schema.json
```

### Expected Output (stdout)
```json
{
  "name": "Charlie Davis",
  "age": 41,
  "role": "DevOps Specialist",
  "skills": [
    "kubernetes",
    "terraform"
  ],
  "active": true
}
```

---

## 3. Fixing Single Quotes

### Command
```bash
python -m structfix --input tests/fixtures/single_quotes.json --schema tests/fixtures/schema.json
```

### Expected Output (stdout)
```json
{
  "name": "Dana Lee",
  "age": 27,
  "role": "Data Scientist",
  "skills": [
    "pytorch",
    "pandas"
  ],
  "active": true
}
```

---

## 4. Safe Schema-Guided Type Coercion

### Command
```bash
python -m structfix --input tests/fixtures/wrong_type.json --schema tests/fixtures/schema.json
```

### Expected Output (stdout)
```json
{
  "name": "Evan Wright",
  "age": 32,
  "role": "Frontend Engineer",
  "skills": [
    "typescript",
    "react"
  ],
  "active": true
}
```
