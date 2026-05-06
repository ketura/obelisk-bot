"""Audit: compare unit logic JSON against views, surface gaps.

The views file declares which named abilities/passives a unit displays.
The logic file declares the mechanics. The audit's job is to flag content
in the logic that isn't reflected in the views — this is where patterns
Unfrozen adds in future patches will first surface.

Per D-017, this audit no longer drives emission. It's a maintenance report
written to ``out/audit.json``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from obelisk.match.patterns import Match  # noqa: F401 — re-exported for compat
from obelisk.models.unit import Unit


_KNOWN_STAT_KEYS: frozenset[str] = frozenset(
    {
        "hp", "offence", "defence", "damageMin", "damageMax",
        "initiative", "speed", "luck", "moral",
        "energyPerCast", "energyPerRound", "energyPerTakeDamage",
        "actionPoints", "numCounters",
        "moralMin", "moralMax", "luckMin", "luckMax",
        "moveType", "inDmgMods", "outDmgMods",
    }
)


@dataclass
class UnitAudit:
    unit_id: str
    family_root: str | None = None
    views_present: bool = False
    notes: list[str] = field(default_factory=list)
    """Free-form maintainer-facing observations, e.g.
    'logic.passives[3] has actions block but no corresponding views entry'."""


@dataclass
class AuditReport:
    units: list[UnitAudit] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        units_missing_views = sum(1 for u in self.units if not u.views_present)
        units_with_notes = sum(1 for u in self.units if u.notes)

        # Reverse index: group identical note text across units. Lets the
        # maintainer see "this same anomaly happens on 23 units" at a glance
        # rather than scanning the per-unit list. Sorted by count descending.
        note_to_units: dict[str, list[str]] = {}
        for u in self.units:
            for note in u.notes:
                note_to_units.setdefault(note, []).append(u.unit_id)
        note_index = sorted(
            (
                {
                    "note": note,
                    "count": len(unit_ids),
                    "units": sorted(unit_ids),
                }
                for note, unit_ids in note_to_units.items()
            ),
            key=lambda entry: (-entry["count"], entry["note"]),
        )

        return {
            "summary": {
                "total_units": len(self.units),
                "units_missing_views": units_missing_views,
                "units_with_notes": units_with_notes,
                "distinct_note_count": len(note_index),
            },
            "note_index": note_index,
            "units": [
                {
                    "unit_id": u.unit_id,
                    "family_root": u.family_root,
                    "views_present": u.views_present,
                    "notes": u.notes,
                }
                for u in self.units
            ],
        }


def audit_unit(
    *,
    unit: Unit,
    views_entry: dict[str, Any] | None,
    family_root: str | None,
) -> UnitAudit:
    """Compare a unit's logic JSON against its views entry; produce notes."""
    audit = UnitAudit(
        unit_id=unit.id,
        family_root=family_root,
        views_present=views_entry is not None,
    )
    if views_entry is None:
        audit.notes.append("no views file entry — unit has no display data")
        return audit

    # Stat fields not in UnitStats and not consumed elsewhere — surface so
    # maintainers can decide if they need a new column or a base-passive
    # lookup mapping.
    for key in unit.raw_stats:
        if key in _KNOWN_STAT_KEYS:
            continue
        audit.notes.append(f"unrecognized stat field: stats.{key}")

    # Logic JSON has more passive blocks than the views lists — possibly
    # internal mechanics or a missing views entry.
    n_logic_passives = sum(
        1
        for p in unit.raw_passives
        if isinstance(p, dict) and any(k in p for k in ("actions", "data"))
    )
    n_view_passives = len(views_entry.get("passives", []) or [])
    if n_logic_passives > n_view_passives:
        audit.notes.append(
            f"logic has {n_logic_passives} passive blocks but views lists {n_view_passives}"
        )

    n_logic_abilities = sum(
        1 for a in unit.raw_abilities if isinstance(a, dict)
    )
    n_view_abilities = len(views_entry.get("abilities", []) or [])
    if n_logic_abilities > n_view_abilities:
        audit.notes.append(
            f"logic has {n_logic_abilities} ability blocks but views lists {n_view_abilities}"
        )

    if unit.aura is not None:
        audit.notes.append("unit has 'aura' block in logic — coverage TBD")

    if unit.raw_conditional_passives:
        audit.notes.append(
            f"unit has {len(unit.raw_conditional_passives)} conditional passive(s) — coverage TBD"
        )
    if unit.raw_global_passives:
        audit.notes.append(
            f"unit has {len(unit.raw_global_passives)} global passive(s) — coverage TBD"
        )

    return audit


def write_audit(report: AuditReport, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report.to_json_dict(), indent=2, sort_keys=False, ensure_ascii=False),
        encoding="utf-8",
    )
