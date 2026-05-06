"""Spell extraction.

Walks ``DB/magics/*.json`` (battle, world, special, test) and emits
SpellRecord + SpellRankRecord per D-030.

Source quirks:

* ``description``/``manaCost`` arrays are length-4 (one per mastery
  level: 1=no skill, 2=basic, 3=advanced, 4=expert) for almost
  every spell.
* ``upgradeCost`` is length-3 for ranked spells (cost paid to
  unlock levels 2/3/4) and length-1 for some flat-cost world spells.
* ``bonusDescriptions`` is either empty or 3 entries with
  ``{level: 2|3|4, description: <SID>}`` — the unlock blurb for each
  upgrade.
* ``learnCost`` is 3 entries (gemstones/crystals/mercury) for most
  spells, or 1 entry (starDust) for unique-magic specials.
"""

from __future__ import annotations

from typing import Any

from obelisk.extract.loader import CorePaths, iter_array, load_json
from obelisk.models.common import Sid
from obelisk.models.spell import (
    SpellExtractionResult,
    SpellRankRecord,
    SpellRecord,
)


_RESOURCE_COLUMN: dict[str, str] = {
    "gemstones": "learn_cost_gemstones",
    "crystals": "learn_cost_crystals",
    "mercury": "learn_cost_mercury",
    "starDust": "learn_cost_star_dust",
}


def _split_learn_cost(raw: list[Any]) -> dict[str, int]:
    """Map source ``learnCost`` array to per-resource columns.
    Unknown resource names are silently dropped (no spell uses gold/wood/etc.
    for learn cost in the 2026-05-03 corpus)."""
    out: dict[str, int] = {}
    for entry in raw or ():
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        cost = entry.get("cost")
        col = _RESOURCE_COLUMN.get(name) if isinstance(name, str) else None
        if col is None or not isinstance(cost, (int, float)):
            continue
        out[col] = int(cost)
    return out


def _build_ranks(
    spell_id: str,
    descriptions: list[Any],
    mana_costs: list[Any],
    upgrade_costs: list[Any],
    bonus_descs: list[Any],
) -> tuple[SpellRankRecord, ...]:
    """Build the 4 SpellRank rows.

    Indexing convention (per D-030):

    * description[0..3] / manaCost[0..3] map to levels 1..4.
    * upgradeCost[0..2] is the cost paid to reach levels 2/3/4
      (length-1 sources fall back to populating only level 2).
    * bonusDescriptions entries are keyed by their explicit ``level``
      (2/3/4) — assigned to the matching SpellRank row.
    """
    bonus_by_level: dict[int, Sid] = {}
    for bd in bonus_descs or ():
        if not isinstance(bd, dict):
            continue
        lvl = bd.get("level")
        sid = bd.get("description")
        if isinstance(lvl, int) and isinstance(sid, str):
            bonus_by_level[lvl] = sid

    upgrade_by_level: dict[int, int] = {}
    for i, cost in enumerate(upgrade_costs or ()):
        target_level = i + 2  # upgrade_costs[0] → reach level 2
        if isinstance(cost, (int, float)) and target_level in (2, 3, 4):
            upgrade_by_level[target_level] = int(cost)

    rows: list[SpellRankRecord] = []
    for level in (1, 2, 3, 4):
        idx = level - 1
        desc_sid = (
            descriptions[idx]
            if idx < len(descriptions) and isinstance(descriptions[idx], str)
            else None
        )
        mana = (
            int(mana_costs[idx])
            if idx < len(mana_costs) and isinstance(mana_costs[idx], (int, float))
            else None
        )
        rows.append(
            SpellRankRecord(
                spell_id=spell_id,
                level=level,
                description_sid=desc_sid,
                mana_cost=mana,
                bonus_description_sid=bonus_by_level.get(level),
                upgrade_cost=upgrade_by_level.get(level),
            )
        )
    return tuple(rows)


def _build_spell(raw: dict[str, Any], source_path: str) -> SpellRecord | None:
    spell_id = raw.get("id")
    if not isinstance(spell_id, str):
        return None

    learn_cost = _split_learn_cost(raw.get("learnCost") or [])
    ranks = _build_ranks(
        spell_id,
        raw.get("description") or [],
        raw.get("manaCost") or [],
        raw.get("upgradeCost") or [],
        raw.get("bonusDescriptions") or [],
    )

    return SpellRecord(
        id=spell_id,
        name_sid=str(raw.get("name", "")),
        icon=str(raw.get("icon", "")),
        school=str(raw.get("school_", "")),
        rank=int(raw.get("rank", 0)),
        used_on_map=bool(raw.get("usedOnMap", False)),
        magic_type_description=(
            raw["magicTypeDescription"]
            if isinstance(raw.get("magicTypeDescription"), str) else None
        ),
        is_special_magic=bool(raw.get("isSpecialMagic", False)),
        is_unique_magic=bool(raw.get("isUniqueMagic", False)),
        normal_magic_sid=(
            raw["normalMagicSid"] if isinstance(raw.get("normalMagicSid"), str) else None
        ),
        learn_cost_gemstones=learn_cost.get("learn_cost_gemstones"),
        learn_cost_crystals=learn_cost.get("learn_cost_crystals"),
        learn_cost_mercury=learn_cost.get("learn_cost_mercury"),
        learn_cost_star_dust=learn_cost.get("learn_cost_star_dust"),
        excaption_in_tooltip_sid=(
            raw["excaptionInTooltip"]
            if isinstance(raw.get("excaptionInTooltip"), str) else None
        ),
        up_effect_description_sid=(
            raw["upEffectDescription"]
            if isinstance(raw.get("upEffectDescription"), str) else None
        ),
        use_expand_tooltip=(
            bool(raw["useExpandTooltip"])
            if isinstance(raw.get("useExpandTooltip"), bool) else None
        ),
        energy_cost=(
            int(raw["energyCost"])
            if isinstance(raw.get("energyCost"), (int, float)) else None
        ),
        energy_type=(
            raw["energyType"] if isinstance(raw.get("energyType"), str) else None
        ),
        ranks=ranks,
        source_path=source_path,
        raw_json=raw,
    )


def extract_spells(paths: CorePaths) -> SpellExtractionResult:
    """Walk ``DB/magics/*.json`` and return all SpellRecord entries.
    Per D-030 scope: includes battle, world, _special, and test files.
    """
    out: list[SpellRecord] = []
    for p in sorted((paths.db / "magics").glob("*.json")):
        rel = p.relative_to(paths.core_root).as_posix()
        doc = load_json(p)
        for raw in iter_array(doc):
            if not isinstance(raw, dict):
                continue
            spell = _build_spell(raw, source_path=rel)
            if spell is not None:
                out.append(spell)
    out.sort(key=lambda s: s.id)
    return SpellExtractionResult(spells=tuple(out))
