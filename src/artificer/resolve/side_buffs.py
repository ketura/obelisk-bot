"""Load ``Core/DB/side_buffs/`` into an info -> base lookup.

OE has two side-buff tiers:

* ``side_buff_infos/*.json`` — application records keyed by id, holding an
  ``allegiance``, ``duration``, ``durationPerStack``, and a ``sid`` pointer.
* ``side_buff_base/*.json`` — effect bases keyed by id, holding the actual
  ``heroStat`` block (or other typed payload).

The script-language ``DbSideBuff(target, info_id, "json.path")`` op reads
``info_id`` from infos, follows its ``sid`` to the matching base, and reads
``json.path`` from there. Mirrors :class:`BuffIndex` and
:class:`ObstacleIndex`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SideBuffIndex:
    """Two-tier side-buff lookup."""

    def __init__(self) -> None:
        self._infos: dict[str, dict[str, Any]] = {}
        self._bases: dict[str, dict[str, Any]] = {}

    def load_dir(self, root: Path) -> None:
        if not root.is_dir():
            return
        infos_dir = root / "side_buff_infos"
        bases_dir = root / "side_buff_base"
        self._load_into(infos_dir, self._infos)
        self._load_into(bases_dir, self._bases)

    @staticmethod
    def _load_into(root: Path, target: dict[str, dict[str, Any]]) -> None:
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
                eid = entry.get("id")
                if isinstance(eid, str):
                    target[eid] = entry

    def get_effect(self, info_id: str) -> dict[str, Any] | None:
        """Resolve ``info_id`` -> info -> base, return the base dict."""
        info = self._infos.get(info_id)
        if info is None:
            return None
        sid = info.get("sid")
        if not isinstance(sid, str):
            return None
        return self._bases.get(sid)

    def __len__(self) -> int:
        return len(self._infos)


def load_side_buff_index(side_buffs_root: Path) -> SideBuffIndex:
    idx = SideBuffIndex()
    idx.load_dir(side_buffs_root)
    return idx
