"""Result data models for StructFix."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any


@dataclass
class RepairResult:
    """Represents the outcome of a StructFix repair process.

    Attributes:
        status: "success", "unrecoverable", or "failed"
        tier_used: 0 (already valid), 1 (Tier 1 deterministic), 2 (Tier 2 AI), or None/0 if failed
        attempts: Total repair cycles attempted
        ai_calls: Number of AI calls made (0 for Tier 1)
        latency_ms: Total execution time in milliseconds
        strategies_applied: List of repair operations applied (e.g. 'strip_markdown_fences', 'coerce_type:$.age')
        data: The parsed/repaired data (or None if unparseable)
        errors: List of remaining validation errors if any
        unrecoverable_fields: List of required fields that could not be recovered and were set to null
    """

    status: str  # "success" | "unrecoverable" | "failed"
    tier_used: int | None = None
    attempts: int = 0
    ai_calls: int = 0
    latency_ms: float = 0.0
    strategies_applied: list[str] = field(default_factory=list)
    data: Any = None
    errors: list[str] = field(default_factory=list)
    unrecoverable_fields: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Return True if the data is valid JSON meeting schema or unrecoverable with explicit nulls."""
        return self.status in ("success", "unrecoverable") and len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
