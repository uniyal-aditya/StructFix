"""Unit tests for StructFix JSON Schema Validator."""

import pytest
from structfix.repair.validator import find_missing_required_fields, format_json_path, validate


@pytest.fixture
def user_schema():
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "email": {"type": "string"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
            },
            "profile": {
                "type": "object",
                "properties": {
                    "bio": {"type": "string"},
                    "score": {"type": "number"},
                },
                "required": ["bio"],
            },
        },
        "required": ["name", "age"],
    }


def test_valid_data(user_schema):
    data = {
        "name": "Alice",
        "age": 30,
        "email": "alice@example.com",
        "tags": ["admin", "developer"],
        "profile": {"bio": "Software engineer", "score": 99.5},
    }
    ok, errors = validate(data, user_schema)
    assert ok is True
    assert errors == []


def test_missing_required_field(user_schema):
    # Missing 'age'
    data = {
        "name": "Bob",
        "email": "bob@example.com",
    }
    ok, errors = validate(data, user_schema)
    assert ok is False
    assert len(errors) >= 1
    assert any("age" in err and "$" in err for err in errors)

    missing = find_missing_required_fields(data, user_schema)
    assert "age" in missing


def test_wrong_type(user_schema):
    # 'age' is a string instead of integer, score is a boolean instead of number
    data = {
        "name": "Charlie",
        "age": "thirty",
        "profile": {"bio": "Dev", "score": True},
    }
    ok, errors = validate(data, user_schema)
    assert ok is False
    assert len(errors) >= 1
    assert any("$.age" in err for err in errors)


def test_nested_array_wrong_type(user_schema):
    data = {
        "name": "David",
        "age": 25,
        "tags": ["dev", 12345],  # 12345 is wrong type
    }
    ok, errors = validate(data, user_schema)
    assert ok is False
    assert any("$.tags[1]" in err for err in errors)


def test_format_json_path():
    assert format_json_path([]) == "$"
    assert format_json_path(["user", "address", "city"]) == "$.user.address.city"
    assert format_json_path(["items", 0, "name"]) == "$.items[0].name"
