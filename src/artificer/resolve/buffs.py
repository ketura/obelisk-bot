"""Load ``Core/DB/buffs/*.json`` into an id-keyed lookup.

Each buff file is a ``{"array": [...]}`` wrapper with entries keyed by ``id``.
Used by the script-language ``DbBuff(target, buff_sid, "json.path")`` op,
which reads a path from the named buff's JSON entry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class BuffIndex:
    """Buff id → buff JSON entry."""

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
                bid = entry.get("id")
                if isinstance(bid, str):
                    self._map[bid] = entry

    def get(self, buff_id: str) -> dict[str, Any] | None:
        return self._map.get(buff_id)

    def __len__(self) -> int:
        return len(self._map)


def load_buff_index(buffs_root: Path) -> BuffIndex:
    idx = BuffIndex()
    idx.load_dir(buffs_root)
    return idx
