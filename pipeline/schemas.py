"""Schema validation for the inter-agent contracts.

Validates each agent's JSON output against the JSON-Schema files in ../schemas
*before* it is handed to the next agent. A failure raises loudly — the
orchestrator aborts rather than forwarding malformed data across an agent
boundary (see CLAUDE.md → Orchestrator design rules).

Note: schemas/schema_a.json and schemas/schema_b.json are the canonical example
contracts and are intentionally left untouched. The *.schema.json files here are
the machine-checkable versions derived from them.
"""

from __future__ import annotations

import json
import pathlib

import jsonschema

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent.parent / "schemas"


class SchemaValidationError(Exception):
    """Raised when an agent's output does not satisfy its contract."""


def _load(filename: str) -> dict:
    return json.loads((SCHEMA_DIR / filename).read_text(encoding="utf-8"))


def _validate(data: dict, filename: str, *, label: str) -> dict:
    schema = _load(filename)
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        location = "/".join(str(p) for p in exc.path) or "<root>"
        raise SchemaValidationError(
            f"{label} failed {filename} validation at '{location}': {exc.message}"
        ) from exc
    return data


def validate_schema_a(data: dict) -> dict:
    """Validate Agent 0's output (the structured story)."""
    return _validate(data, "schema_a.schema.json", label="Agent 0 output (schema_a)")


def validate_schema_b(data: dict) -> dict:
    """Validate Agent 1's output (the test scenarios)."""
    return _validate(data, "schema_b.schema.json", label="Agent 1 output (schema_b)")
