"""End-to-end and unit tests for StructFix CLI."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from structfix.cli import main


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def schema_path(fixtures_dir):
    return str(fixtures_dir / "schema.json")


def test_cli_valid_fixture(fixtures_dir, schema_path, capsys):
    input_file = str(fixtures_dir / "valid.json")
    code = main(["--input", input_file, "--schema", schema_path, "--no-tier2"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["name"] == "Alice Johnson"


def test_cli_fenced_fixture(fixtures_dir, schema_path, capsys):
    input_file = str(fixtures_dir / "fenced.json")
    code = main(["--input", input_file, "--schema", schema_path, "--no-tier2"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["name"] == "Bob Smith"


def test_cli_trailing_comma_fixture(fixtures_dir, schema_path, capsys):
    input_file = str(fixtures_dir / "trailing_comma.json")
    code = main(["--input", input_file, "--schema", schema_path, "--no-tier2"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["name"] == "Charlie Davis"


def test_cli_single_quotes_fixture(fixtures_dir, schema_path, capsys):
    input_file = str(fixtures_dir / "single_quotes.json")
    code = main(["--input", input_file, "--schema", schema_path, "--no-tier2"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["name"] == "Dana Lee"


def test_cli_wrong_type_fixture(fixtures_dir, schema_path, capsys):
    input_file = str(fixtures_dir / "wrong_type.json")
    code = main(["--input", input_file, "--schema", schema_path, "--no-tier2"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["name"] == "Evan Wright"
    assert data["age"] == 32


def test_cli_missing_file_usage_error(capsys):
    code = main(["--input", "non_existent_file.json", "--schema", "non_existent_schema.json"])
    assert code == 2
    captured = capsys.readouterr()
    assert "Input file not found" in captured.err


def test_cli_unrepairable_tier1(fixtures_dir, schema_path, capsys):
    input_file = str(fixtures_dir / "missing_age.json")
    code = main(["--input", input_file, "--schema", schema_path, "--no-tier2"])
    assert code == 1
    captured = capsys.readouterr()
    assert "StructFix Error: Failed to repair JSON." in captured.err


def test_cli_tier2_mocked(fixtures_dir, schema_path, capsys):
    input_file = str(fixtures_dir / "missing_age.json")
    mock_response = json.dumps({
        "name": "Fiona Gallagher",
        "age": 38,
        "role": "Senior SRE",
        "skills": ["AWS", "Go", "Prometheus"],
        "active": True,
    })

    with patch("structfix.models.client.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": mock_response}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        code = main(["--input", input_file, "--schema", schema_path, "--model", "qwen3:1.7b"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["name"] == "Fiona Gallagher"
        assert data["age"] == 38
