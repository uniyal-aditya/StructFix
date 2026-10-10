"""Tests for StructFix Flask Web Application and REST API."""

import json
from unittest.mock import patch, MagicMock
import pytest
from structfix.web import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_get_index(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"StructFix" in res.data
    assert b"Generate. Validate. Repair. Trust." in res.data


def test_get_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert "ollama" in data
    assert data["ollama"]["configured_model"] == "qwen3:1.7b"


def test_get_examples(client):
    res = client.get("/api/examples")
    assert res.status_code == 200
    data = res.get_json()
    assert "examples" in data
    assert len(data["examples"]) >= 5
    example_ids = [ex["id"] for ex in data["examples"]]
    assert "valid" in example_ids
    assert "fenced" in example_ids
    assert "trailing_comma.json" in [ex.get("file", "") for ex in data["examples"]] or "trailing_comma" in example_ids


def test_post_repair_deterministic(client):
    payload = {
        "input": "```json\n{'name': 'Alice', 'age': '30',}\n```",
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name", "age"],
        },
        "enable_ai": False,
    }
    res = client.post("/api/repair", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["is_valid"] is True
    assert data["status"] == "valid"
    assert data["tier_used"] == 1
    assert data["data"] == {"name": "Alice", "age": 30}


def test_post_repair_invalid_schema(client):
    payload = {
        "input": '{"name": "Alice"}',
        "schema": "this is not valid json schema",
    }
    res = client.post("/api/repair", json=payload)
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data


def test_post_repair_non_json_body(client):
    res = client.post("/api/repair", data="raw text not json", content_type="text/plain")
    assert res.status_code == 400


def test_post_repair_mocked_ai(client):
    ai_mock_response = json.dumps({
        "name": "Fiona Gallagher",
        "age": 38,
        "role": "Senior SRE",
        "skills": ["AWS", "Go"],
        "active": True,
    })

    with patch("structfix.models.client.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": ai_mock_response}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        payload = {
            "input": "Candidate: Fiona Gallagher, Age: 38 years old, Role: Senior SRE",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "role": {"type": "string"},
                },
                "required": ["name", "age"],
            },
            "model": "qwen3:1.7b",
            "enable_ai": True,
            "max_retries": 2,
        }
        res = client.post("/api/repair", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["is_valid"] is True
        assert data["tier_used"] == 2
        assert data["ai_calls"] >= 1
        assert data["data"]["name"] == "Fiona Gallagher"
        assert data["data"]["age"] == 38
