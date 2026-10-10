"""JSON Schema Validation Module for StructFix.

Validates parsed JSON against a JSON Schema and produces human-readable
error messages with precise JSON paths.
"""

from __future__ import annotations

from typing import Any
import jsonschema
from jsonschema.validators import validator_for


def format_json_path(path_deque: list[Any]) -> str:
    """Format a jsonschema error path into a clean JSONPath string (e.g. $.user.address[0].city)."""
    if not path_deque:
        return "$"
    path_str = "$"
    for elem in path_deque:
        if isinstance(elem, int):
            path_str += f"[{elem}]"
        else:
            path_str += f".{elem}"
    return path_str


def validate_schema(schema: Any) -> tuple[bool, str | None]:
    """Validate that the schema itself is a valid JSON Schema."""
    if not isinstance(schema, dict):
        return False, "Schema must be a JSON object"
    try:
        validator_cls = validator_for(schema)
        validator_cls.check_schema(schema)
        return True, None
    except jsonschema.exceptions.SchemaError as e:
        return False, str(e.message)
    except Exception as e:
        return False, str(e)


def validate(data: Any, schema: dict[str, Any] | None) -> tuple[bool, list[str]]:
    """Validate data against a JSON schema.

    Returns:
        (is_valid: bool, errors: list[str])
    """
    if schema is None:
        return True, []

    # Verify schema itself first
    schema_ok, schema_err = validate_schema(schema)
    if not schema_ok:
        return False, [f"Invalid JSON Schema: {schema_err}"]

    validator_cls = validator_for(schema)
    try:
        validator = validator_cls(schema)
    except Exception as e:
        return False, [f"Invalid JSON Schema definition: {e}"]

    raw_errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if not raw_errors:
        return True, []

    formatted_errors: list[str] = []
    for err in raw_errors:
        path = format_json_path(list(err.path))

        # Handle required property errors specifically for clearer reporting
        if err.validator == "required":
            missing_prop = err.validator_value
            if isinstance(missing_prop, list):
                # When jsonschema checks required list
                missing_prop = ", ".join(f"'{p}'" for p in err.message.split("'")[1::2]) or str(err.validator_value)
            formatted_errors.append(f"At {path}: Missing required field {missing_prop} ({err.message})")
        else:
            formatted_errors.append(f"At {path}: {err.message}")

    return False, formatted_errors


def find_missing_required_fields(data: Any, schema: dict[str, Any] | None) -> list[str]:
    """Identify required fields that are missing or null in the data."""
    if not schema or not isinstance(schema, dict) or not isinstance(data, dict):
        return []

    missing: list[str] = []
    required = schema.get("required", [])
    for field in required:
        if field not in data or data[field] is None:
            missing.append(field)
    return missing
