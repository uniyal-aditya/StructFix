"""StructFix: Lightweight, local-first Python CLI harness to repair malformed LLM JSON output."""

from structfix.engine import repair
from structfix.models.result import RepairResult

__version__ = "0.1.0"
__all__ = ["repair", "RepairResult"]
