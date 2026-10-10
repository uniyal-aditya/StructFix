"""Unit and integration tests for StructFix Repair Engine."""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from structfix.engine import repair
from structfix.models.result import RepairResult
from structfix.repair.client import OllamaClient


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def schema_dict(fixtures_dir):
    return json.loads((fixtures_dir / "schema.json").read_text())


def test_engine_valid_fixture(fixtures_dir, schema_dict):
    raw = (fixtures_dir / "valid.json").read_text()
    result = repair(raw, schema_dict, enable_tier2=False)
    assert result.status == "success"
    assert result.tier_used == 0
    assert result.attempts == 0
    assert result.ai_calls == 0
    assert result.is_valid is True
    assert result.data["name"] == "Alice Johnson"


def test_engine_fenced_fixture(fixtures_dir, schema_dict):
    raw = (fixtures_dir / "fenced.json").read_text()
    result = repair(raw, schema_dict, enable_tier2=False)
    assert result.status == "success"
    assert result.tier_used == 1
    assert result.is_valid is True
    assert result.data["name"] == "Bob Smith"
    assert any("strip_markdown_fences" in s for s in result.strategies_applied)


def test_engine_trailing_comma_fixture(fixtures_dir, schema_dict):
    raw = (fixtures_dir / "trailing_comma.json").read_text()
    result = repair(raw, schema_dict, enable_tier2=False)
    assert result.status == "success"
    assert result.tier_used == 1
    assert result.is_valid is True
    assert result.data["name"] == "Charlie Davis"


def test_engine_single_quotes_fixture(fixtures_dir, schema_dict):
    raw = (fixtures_dir / "single_quotes.json").read_text()
    result = repair(raw, schema_dict, enable_tier2=False)
    assert result.status == "success"
    assert result.tier_used == 1
    assert result.is_valid is True
    assert result.data["name"] == "Dana Lee"


def test_engine_wrong_type_fixture(fixtures_dir, schema_dict):
    raw = (fixtures_dir / "wrong_type.json").read_text()
    result = repair(raw, schema_dict, enable_tier2=False)
    assert result.status == "success"
    assert result.tier_used == 1
    assert result.is_valid is True
    assert result.data["name"] == "Evan Wright"
    assert result.data["age"] == 32
    assert result.data["active"] is True


def test_engine_tier2_fallback(fixtures_dir, schema_dict):
    raw = (fixtures_dir / "missing_age.json").read_text()
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.return_value = json.dumps({
        "name": "Fiona Gallagher",
        "age": 38,
        "role": "Senior SRE",
        "skills": ["AWS", "Go", "Prometheus"],
        "active": True,
    })

    result = repair(raw, schema_dict, client=mock_client, model="qwen3:1.7b")
    assert result.status == "success"
    assert result.tier_used == 2
    assert result.ai_calls == 1
    assert result.data["age"] == 38
    assert result.is_valid is True
