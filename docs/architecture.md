# StructFix Architecture

This document provides a deep dive into the internal design and mechanics of StructFix.

## Core Design Principles

1. **Local-First & Decoupled**: Functions as an independent CLI utility and Python library without dependencies on cloud APIs or heavy server frameworks.
2. **Deterministic-First (Tier 1)**: Syntax and formatting problems are solved in `< 1ms` with 0 token costs and 0 latency overhead.
3. **Bounded AI Fallback (Tier 2)**: Engages local open-weight models (Qwen3, Llama 3.2 via Ollama) only when semantic re-structuring is necessary.
4. **Zero-Hallucination Guarantee Policy**: StructFix strictly forbids fabricating missing required fields. If data is absent, it returns `null` and records the field as unrecoverable.

---

## Component Walkthrough

### 1. `structfix.repair.parser` (Tier 1 Engine)

The deterministic parser executes sequential transformation passes:
- **Thinking Token Stripping**: Removes `<think>...</think>` blocks (including unclosed reasoning prefixes).
- **Markdown Code Fence Extraction**: Detects ```` ```json ... ``` ```` blocks and extracts inner content.
- **Prose Extraction**: Balanced bracket matcher extracts the root `{ ... }` or `[ ... ]` substring from conversational wrapper text.
- **Syntax Correction**: Uses fast character heuristics and `json-repair` to resolve single quotes and trailing commas.
- **Safe Type Coercion**: Guided by JSON Schema, safely parses string numbers (`"19.99"` -> `19.99`), booleans (`"true"` -> `True`), and null strings without guessing ambiguous domain values.

### 2. `structfix.repair.validator` (Validation Layer)

- Uses `jsonschema` with full Draft-07 / Draft-2020-12 support.
- Produces normalized JSONPath strings (e.g. `$.users[0].profile.age`) and human-readable error descriptions.
- Identifies missing required fields.

### 3. `structfix.repair.client` & `structfix.repair.ai_repair` (Tier 2 Engine)

- Communicates with Ollama at `http://localhost:11434` (`/api/generate`).
- Passes the JSON Schema to Ollama's `format` parameter to constrain model token generation.
- Executes bounded retries (maximum 3 attempts) feeding back remaining validation errors at each step.

### 4. `structfix.models.result`

The `RepairResult` model encapsulates detailed execution telemetry:
- `status`: `"success"` | `"unrecoverable"` | `"failed"`
- `tier_used`: `0` (pristine), `1` (Tier 1 deterministic), `2` (Tier 2 AI)
- `attempts`: Total repair cycles
- `ai_calls`: AI generation requests executed
- `latency_ms`: Execution time in milliseconds
- `strategies_applied`: Chronological log of applied transformations
- `unrecoverable_fields`: List of schema-required fields that could not be derived from input text
