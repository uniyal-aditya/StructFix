"""Unit tests for Tier 2 AI Repair with mocked OllamaClient."""

import json
from unittest.mock import MagicMock
import pytest
from structfix.repair.ai_repair import repair_with_ai
from structfix.repair.client import OllamaClient


@pytest.fixture
def target_schema():
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": ["integer", "null"]},
            "role": {"type": "string"},
        },
        "required": ["name", "age"],
    }


def test_ai_repair_success_attempt_1(target_schema):
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.return_value = '{"name": "Alice", "age": 30, "role": "developer"}'

    raw_input = "User: Alice, role: developer, age is thirty something"
    data, is_valid, strategies, ai_calls, errors, unrec = repair_with_ai(
        raw_text=raw_input,
        schema=target_schema,
        client=mock_client,
        model="qwen3:1.7b",
        max_retries=3,
    )

    assert is_valid is True
    assert ai_calls == 1
    assert data == {"name": "Alice", "age": 30, "role": "developer"}
    assert errors == []
    assert unrec == []
    assert any("tier2_ai_attempt_1:qwen3:1.7b" in s for s in strategies)
    mock_client.generate.assert_called_once()


def test_ai_repair_success_attempt_2(target_schema):
    mock_client = MagicMock(spec=OllamaClient)
    # Attempt 1 returns missing age (invalid)
    # Attempt 2 returns valid object
    mock_client.generate.side_effect = [
        '{"name": "Bob", "role": "manager"}',  # missing 'age'
        '{"name": "Bob", "age": 45, "role": "manager"}',
    ]

    raw_input = "Bob is a manager, age 45."
    data, is_valid, strategies, ai_calls, errors, unrec = repair_with_ai(
        raw_text=raw_input,
        schema=target_schema,
        client=mock_client,
        model="llama3.2",
        max_retries=3,
    )

    assert is_valid is True
    assert ai_calls == 2
    assert data == {"name": "Bob", "age": 45, "role": "manager"}
    assert errors == []
    assert any("tier2_ai_attempt_2:llama3.2" in s for s in strategies)
    assert mock_client.generate.call_count == 2


def test_ai_repair_exhaustion(target_schema):
    mock_client = MagicMock(spec=OllamaClient)
    # All 3 attempts return invalid JSON or schema violations
    mock_client.generate.side_effect = [
        '{"name": "Charlie"}',  # attempt 1: missing age
        '{"name": "Charlie", "age": "still_invalid"}',  # attempt 2: wrong type
        '{"name": "Charlie", "age": "unknown"}',  # attempt 3: wrong type
    ]

    raw_input = "Charlie has unknown age"
    data, is_valid, strategies, ai_calls, errors, unrec = repair_with_ai(
        raw_text=raw_input,
        schema=target_schema,
        client=mock_client,
        model="qwen3:1.7b",
        max_retries=3,
    )

    assert is_valid is False
    assert ai_calls == 3
    assert len(errors) > 0
    assert mock_client.generate.call_count == 3


def test_ai_repair_unrecoverable_field(target_schema):
    mock_client = MagicMock(spec=OllamaClient)
    # Model returns null for unknown required field as per rule
    mock_client.generate.return_value = '{"name": "Dana", "age": null, "role": "analyst"}'

    raw_input = "Dana is an analyst, no age provided in text."
    data, is_valid, strategies, ai_calls, errors, unrec = repair_with_ai(
        raw_text=raw_input,
        schema=target_schema,
        client=mock_client,
        model="qwen3:1.7b",
        max_retries=3,
    )

    assert is_valid is True
    assert data["name"] == "Dana"
    assert data["age"] is None
    assert "age" in unrec
