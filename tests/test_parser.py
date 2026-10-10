"""Unit tests for Tier 1 Deterministic Parser."""

import pytest
from structfix.repair.parser import (
    coerce_types,
    extract_json_from_prose,
    fix_single_quotes_and_trailing_commas,
    parse_and_repair_json,
    repair_unclosed_strings,
    strip_markdown_fences,
    strip_thinking_tags,
)


def test_strip_thinking_tags():
    raw = "<think>Let me think about the JSON structure...</think>{\"name\": \"Alice\"}"
    cleaned = strip_thinking_tags(raw)
    assert cleaned == '{"name": "Alice"}'

    unclosed = "<think>Unclosed thinking block... {\"name\": \"Alice\"}"
    cleaned_unclosed = strip_thinking_tags(unclosed)
    assert cleaned_unclosed == ""


def test_strip_markdown_fences():
    # standard markdown fence
    fenced = "```json\n{\n  \"name\": \"Alice\",\n  \"age\": 30\n}\n```"
    assert strip_markdown_fences(fenced) == '{\n  "name": "Alice",\n  "age": 30\n}'

    # generic fence
    generic = "```\n[1, 2, 3]\n```"
    assert strip_markdown_fences(generic) == "[1, 2, 3]"

    # inline fence
    inline = "```json {\"status\": \"ok\"} ```"
    assert strip_markdown_fences(inline) == '{"status": "ok"}'


def test_extract_json_from_prose():
    prose = 'Sure! Here is the JSON output you asked for:\n{"name": "Alice", "age": 30}\nHope this helps!'
    extracted = extract_json_from_prose(prose)
    assert extracted == '{"name": "Alice", "age": 30}'

    nested_prose = 'Result: {"user": {"name": "Bob", "tags": ["admin", "dev"]}, "active": true} Done.'
    assert extract_json_from_prose(nested_prose) == '{"user": {"name": "Bob", "tags": ["admin", "dev"]}, "active": true}'

    array_prose = 'Output list: [{"id": 1}, {"id": 2}] End of list.'
    assert extract_json_from_prose(array_prose) == '[{"id": 1}, {"id": 2}]'


def test_fix_single_quotes_and_trailing_commas():
    # Trailing comma in object
    trailing_obj = '{"name": "Alice", "age": 30,}'
    data, strategies = parse_and_repair_json(trailing_obj)
    assert data == {"name": "Alice", "age": 30}

    # Trailing comma in array
    trailing_arr = '[1, 2, 3, ]'
    data, strategies = parse_and_repair_json(trailing_arr)
    assert data == [1, 2, 3]

    # Single quotes
    single_q = "{'name': 'Alice', 'role': 'engineer'}"
    data, strategies = parse_and_repair_json(single_q)
    assert data == {"name": "Alice", "role": "engineer"}

    # Single quotes with trailing comma
    single_and_trailing = "{'name': 'Alice', 'age': 30, 'skills': ['python', 'ml',],}"
    data, strategies = parse_and_repair_json(single_and_trailing)
    assert data == {"name": "Alice", "age": 30, "skills": ["python", "ml"]}


def test_repair_unclosed_strings():
    # Unclosed string followed by another key (like the user's scenario)
    broken = '{\n  "name": "Bob Smith\n  "age": 34,\n  "role": "Backend Engineer"\n}'
    data, strategies = parse_and_repair_json(broken)
    assert data == {"name": "Bob Smith", "age": 34, "role": "Backend Engineer"}
    assert "repair_unclosed_strings" in strategies

    # Unclosed string before closing brace
    broken_brace = '{\n  "name": "Bob Smith",\n  "role": "Backend Engineer\n}'
    data, strategies = parse_and_repair_json(broken_brace)
    assert data == {"name": "Bob Smith", "role": "Backend Engineer"}


def test_coerce_types_safe():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "price": {"type": "number"},
            "active": {"type": "boolean"},
            "notes": {"type": ["string", "null"]},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "score": {"type": "number"},
                    },
                },
            },
        },
    }

    raw_data = {
        "name": "Widget",
        "age": "30",
        "price": "19.99",
        "active": "true",
        "notes": "null",
        "items": [
            {"id": "101", "score": "98.5"},
            {"id": "102", "score": "75"},
        ],
    }

    coerced, strats = coerce_types(raw_data, schema)
    assert coerced["name"] == "Widget"
    assert coerced["age"] == 30
    assert coerced["price"] == 19.99
    assert coerced["active"] is True
    assert coerced["notes"] is None
    assert coerced["items"][0]["id"] == 101
    assert coerced["items"][0]["score"] == 98.5
    assert coerced["items"][1]["id"] == 102
    assert coerced["items"][1]["score"] == 75.0 or coerced["items"][1]["score"] == 75
    assert len(strats) > 0


def test_coerce_types_unsafe_unaltered():
    schema = {
        "type": "object",
        "properties": {
            "age": {"type": "integer"},
        },
    }
    # Unparseable string should remain as-is for validator to catch
    raw_data = {"age": "thirty"}
    coerced, strats = coerce_types(raw_data, schema)
    assert coerced["age"] == "thirty"
    assert len(strats) == 0


def test_combined_tier1_flow():
    prose_fenced_mess = (
        "<think>Generating user object...</think>\n"
        "Here is your user profile data:\n"
        "```json\n"
        "{\n"
        "  'name': 'Bob',\n"
        "  'age': '42',\n"
        "  'rating': '4.85',\n"
        "}\n"
        "```\n"
        "Let me know if you need anything else!"
    )
    data, strategies = parse_and_repair_json(prose_fenced_mess)
    assert data["name"] == "Bob"

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "rating": {"type": "number"},
        },
    }
    coerced, coerce_strats = coerce_types(data, schema)
    assert coerced == {"name": "Bob", "age": 42, "rating": 4.85}
