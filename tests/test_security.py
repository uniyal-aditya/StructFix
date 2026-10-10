"""Security and input validation tests for StructFix."""

import pytest
from structfix.web import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_payload_size_limit(client):
    # Payload over 2MB limit
    oversized_data = "x" * (2 * 1024 * 1024 + 1024)
    res = client.post(
        "/api/repair",
        json={"input": oversized_data},
    )
    assert res.status_code == 413


def test_malformed_json_body(client):
    res = client.post(
        "/api/repair",
        data="{malformed json",
        content_type="application/json",
    )
    assert res.status_code == 400


def test_invalid_schema_type_rejection(client):
    res = client.post(
        "/api/repair",
        json={"input": "{}", "schema": 12345},
    )
    assert res.status_code == 400
    assert b"must be a JSON object or string" in res.data


def test_invalid_schema_structure_rejection(client):
    # Object that is not a valid JSON schema (e.g. type is an invalid value)
    res = client.post(
        "/api/repair",
        json={"input": "{}", "schema": {"type": "not_a_valid_json_type"}},
    )
    assert res.status_code == 400
    assert b"Invalid JSON Schema" in res.data
