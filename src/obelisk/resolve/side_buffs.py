"""Load ``Core/DB/side_buffs/`` into an info -> base lookup.

OE has three side-buff tiers:

* ``side_buff_infos/*.json`` — application records keyed by id, holding an
  ``allegiance``, ``duration``, ``durationPerStack``, and a ``sid`` pointer.
* ``side_buff_base/*.json`` — side-effect bases keyed by id, holding the
  actual ``heroStat`` block (or other typed payload).
* ``bonus_buff_infos/*.json`` — *unit-applied* sub-skill bonus infos, with
  the same shape as side_buff_infos but whose ``sid`` resolves into the
  unit-buff DB (``Core/DB/buffs/``) rather than ``side_buff_base/``.

The script-language ``DbSideBuff(target, info_id, "json.path")`` op reads
``info_id`` from infos, follows its ``sid`` to the matching base, and reads
``json.path`` from there. To satisfy lookups for sub-skill bonus chains
(e.g. skill_formation: bonuses parameter → bonus_buff_info → sid →
DB/buffs entry → ``actions[0].damageDealer.buff.sid``), the index also
loads ``bonus_buff_infos/`` as additional infos and falls back to a
shared :class:`BuffIndex` when the resolved sid isn't in side_buff_base.

Mirrors :class:`BuffIndex` and :class:`ObstacleIndex`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SideBuffIndex:
    """Two-tier side-buff lookup with bonus-buff fallback."""

    def __init__(self) -> None:
        self._infos: dict[str, dict[str, Any]] = {}
        self._bases: dict[str, dict[str, Any]] = {}
        # Optional buff-index fallback. When the resolved sid isn't in
        # side_buff_base (the typical case for sub-skill bonus chains),
        # we look it up in the unit-buff DB instead.
        self._buff_fallback: Any = None

    def attach_buff_fallback(self, buffs: Any) -> None:
        """Wire a shared :class:`BuffIndex` for fallback resolution.

        Called by :func:`load_side_buff_index` after both indices exist."""
        self._buff_fallback = buffs

    def load_dir(self, root: Path) -> None:
        if not root.is_dir():
            return
        infos_dir = root / "side_buff_infos"
        bases_dir = root / "side_buff_base"
        bonus_infos_dir = root / "bonus_buff_infos"
        self._load_into(infos_dir, self._infos)
        self._load_into(bases_dir, self._bases)
        # bonus_buff_infos has the same shape as side_buff_infos; merge
        # in (existing keys win — no overlap observed in 2026-05-05).
        self._load_into(bonus_infos_dir, self._infos)

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
        """Resolve ``info_id`` -> info -> base, return the base dict.

        Falls back to the attached :class:`BuffIndex` when the resolved
        sid isn't in ``side_buff_base/`` (the bonus_buff_info path: those
        sids resolve into the unit-buff DB at ``Core/DB/buffs/``)."""
        info = self._infos.get(info_id)
        if info is None:
            return None
        sid = info.get("sid")
        if not isinstance(sid, str):
            return None
        base = self._bases.get(sid)
        if base is not None:
            return base
        if self._buff_fallback is not None:
            return self._buff_fallback.get(sid)
        return None

    def __len__(self) -> int:
        return len(self._infos)


def load_side_buff_index(side_buffs_root: Path) -> SideBuffIndex:
    idx = SideBuffIndex()
    idx.load_dir(side_buffs_root)
    return idx
