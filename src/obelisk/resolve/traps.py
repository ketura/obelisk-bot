"""Load ``Core/DB/field_objects/traps/*.json`` into an id-keyed lookup.

Each trap file is a ``{"array": [...]}`` wrapper with entries keyed by ``id``.
Used by the script-language ``DbTrap(target, trap_id, "json.path")`` op,
which reads a path from the named trap's JSON entry. Mirrors
:class:`obelisk.resolve.obstacles.ObstacleIndex`.

Trap entries (e.g. test_traps.json, traps_magic.json, traps_siege.json)
carry a ``damageDealer`` block with the ``minBaseDmg`` / ``minStackPercentDmg``
/ etc. fields that ``current_magic_upgrade_<N>_trap_damage_*`` scripts
read via DbTrap.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TrapIndex:
    """Trap id -> trap JSON entry."""

    def __init__(self) -> None:
        self._map: dict[str, dict[str, Any]] = {}

    def load_dir(self, root: Path) -> None:
        if not root.is_dir():
            return
        for fp in sorted(root.glob("*.json")):
            try:
                with fp.open(encoding="utf-8-sig") as f:
                    doc = json.load(f)
            except Exception:
                continue
            entries = doc.get("array") if isinstance(doc, dict) else None
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                tid = entry.get("id")
                if isinstance(tid, str):
                    self._map[tid] = entry

    def get(self, trap_id: str) -> dict[str, Any] | None:
        return self._map.get(trap_id)

    def __len__(self) -> int:
        return len(self._map)


def load_trap_index(traps_root: Path) -> TrapIndex:
    idx = TrapIndex()
    idx.load_dir(traps_root)
    return idx
