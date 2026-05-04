"""Load ``Core/DB/field_objects/obstacles/*.json`` into an id-keyed lookup.

Each obstacle file is a ``{"array": [...]}`` wrapper with entries keyed by
``id``. Used by the script-language ``DbObstacle(target, obstacle_id, "path")``
op, which reads a path from the named obstacle's JSON entry. Mirrors
:class:`artificer.resolve.buffs.BuffIndex`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ObstacleIndex:
    """Obstacle id -> obstacle JSON entry."""

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
                oid = entry.get("id")
                if isinstance(oid, str):
                    self._map[oid] = entry

    def get(self, obstacle_id: str) -> dict[str, Any] | None:
        return self._map.get(obstacle_id)

    def __len__(self) -> int:
        return len(self._map)


def load_obstacle_index(obstacles_root: Path) -> ObstacleIndex:
    idx = ObstacleIndex()
    idx.load_dir(obstacles_root)
    return idx
