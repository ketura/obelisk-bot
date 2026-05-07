"""Load ``Core/DB/heroes_abilities/heroes_abilities_base/*.json`` into
an id-keyed lookup.

Each entry has ``id`` + ``levels`` (a list of per-level ability dicts).
Used by the script-language ``DbAbility(target, ability_id, level, "json.path")``
op, which reads a path from the named ability's *level-specific* JSON
entry. Mirrors :class:`obelisk.resolve.traps.TrapIndex` /
:class:`obelisk.resolve.buffs.BuffIndex`, but the lookup additionally
indexes into the ``levels[]`` array.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class HeroAbilityIndex:
    """Hero-ability id -> ability JSON entry (with ``levels[]``)."""

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
                aid = entry.get("id")
                if isinstance(aid, str):
                    self._map[aid] = entry

    def get_level(self, ability_id: str, level: int) -> dict[str, Any] | None:
        """Return the per-level dict for the given ability + 0-based level
        index. Returns None if the ability id is unknown or the level is
        out of range."""
        entry = self._map.get(ability_id)
        if entry is None:
            return None
        levels = entry.get("levels")
        if not isinstance(levels, list):
            return None
        if 0 <= level < len(levels):
            level_data = levels[level]
            return level_data if isinstance(level_data, dict) else None
        return None

    def __len__(self) -> int:
        return len(self._map)


def load_hero_ability_index(root: Path) -> HeroAbilityIndex:
    """Build a HeroAbilityIndex from the
    ``DB/heroes_abilities/heroes_abilities_base/`` directory."""
    idx = HeroAbilityIndex()
    idx.load_dir(root)
    return idx
