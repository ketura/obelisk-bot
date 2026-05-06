"""Stub — pattern detectors are no longer used (see D-015).

The views file is the authoritative source for named abilities/passives.
This module remains as an import target for any audit code that still
references ``Match`` or ``run_detectors``; both are no-ops now.

If we later need to flag JSON-shape patterns the views file omits, this is
where new detectors would land — but they should write to the audit, not to
``UnitAbility`` rows.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from obelisk.models.unit import Unit


@dataclass
class Match:
    """Empty match record. Retained for audit-side compatibility."""

    concept: str
    fields_consumed: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


PatternDetector = Callable[[Unit], list[Match]]

PATTERN_DETECTORS: list[PatternDetector] = []


def run_detectors(unit: Unit) -> list[Match]:  # noqa: ARG001 — stub
    """No-op. Returns an empty list. Detectors are not used (D-015)."""
    return []
