"""Faction-law extraction.

Walks ``DB/fractions_laws/*.json`` (six production files, one per
faction, plus two test files). Each entry has identity (id, name,
desc, icon) and a ``parametersPerLevel`` array (1-3 entries) where
each level carries its own ``cost`` and ``bonuses[]``.

A second pass over ``DB/fractions/*.json`` reads ``fractionLawsLines``
to populate per-law tier placement and to emit ``LawTreePosition`` +
``FactionLawTier`` side records. Test laws have no faction tree
placement and end up with ``faction=None`` / ``tier=None``.

See D-033.
"""

from __future__ import annotations

import re
from typing import Any

from obelisk.extract.hero import build_bonus
from obelisk.extract.loader import CorePaths, iter_array, load_json
from obelisk.models.hero import Bonus
from obelisk.models.law import (
    FactionLawTierRecord,
    LawExtractionResult,
    LawLevelRecord,
    LawRecord,
    LawTreePositionRecord,
)


_PROD_FILE_RE = re.compile(r"^fractions_laws_table_(\w+)\.json$")
# fractions_laws_test.json + fractions_laws_test_new.json
_TEST_FILE_RE = re.compile(r"^fractions_laws_test(?:_\w+)?\.json$")
_ID_TRAILING_NUM_RE = re.compile(r"_(\d+)$")


def _parse_ordinal(law_id: str) -> int:
    """Trailing N from fraction_law_human_12 / test_fraction_law_3 etc.
    Returns 0 if no trailing number (shouldn't happen in practice)."""
    m = _ID_TRAILING_NUM_RE.search(law_id)
    return int(m.group(1)) if m else 0


def _build_level(
    raw: dict[str, Any], *, law_id: str, level: int,
) -> LawLevelRecord | None:
    """Map one parametersPerLevel entry to LawLevelRecord. Bonuses
    flow into the unified Bonus table with parent_id=<law_id>_L<level>
    so SpellRank-style joins (LIKE '<law_id>_L%') work."""
    cost_raw = raw.get("cost")
    try:
        cost = int(cost_raw)
    except (TypeError, ValueError):
        return None
    parent_id = f"{law_id}_L{level}"
    bonuses: list[Bonus] = []
    for i, b in enumerate(raw.get("bonuses") or ()):
        if isinstance(b, dict):
            bonus = build_bonus(b, parent_type="law_level",
                                parent_id=parent_id, ordinal=i)
            if bonus is not None:
                bonuses.append(bonus)
    return LawLevelRecord(
        law_id=law_id,
        level=level,
        cost=cost,
        bonuses=tuple(bonuses),
        raw_json=raw,
    )


def _build_law(
    raw: dict[str, Any],
    *,
    source_path: str,
    is_test: bool,
    faction: str | None,
    tier: int | None,
) -> LawRecord | None:
    law_id = raw.get("id")
    if not isinstance(law_id, str):
        return None
    levels: list[LawLevelRecord] = []
    for i, level_raw in enumerate(raw.get("parametersPerLevel") or ()):
        if isinstance(level_raw, dict):
            lvl = _build_level(level_raw, law_id=law_id, level=i + 1)
            if lvl is not None:
                levels.append(lvl)
    return LawRecord(
        id=law_id,
        faction=faction,
        ordinal=_parse_ordinal(law_id),
        tier=tier,
        name_sid=str(raw.get("name", "")),
        desc_sid=str(raw.get("desc", "")),
        icon=str(raw.get("icon", "")),
        levels=tuple(levels),
        test=is_test,
        source_path=source_path,
    )


def _walk_faction_trees(
    paths: CorePaths,
) -> tuple[dict[str, tuple[str, int]],
           list[LawTreePositionRecord],
           list[FactionLawTierRecord]]:
    """Walk DB/fractions/*.json, parse fractionLawsLines into
    (law_id → (faction, tier)) lookup + LawTreePosition + FactionLawTier
    rows. Side index `groups[0]` -> "faction", `groups[1]` -> "army",
    matching the in-game screen labels."""
    placement: dict[str, tuple[str, int]] = {}
    positions: list[LawTreePositionRecord] = []
    tiers_out: list[FactionLawTierRecord] = []
    for fp in sorted((paths.db / "fractions").glob("*.json")):
        doc = load_json(fp)
        for fraction_raw in iter_array(doc):
            if not isinstance(fraction_raw, dict):
                continue
            faction = fraction_raw.get("id")
            if not isinstance(faction, str):
                continue
            lines = fraction_raw.get("fractionLawsLines")
            if not isinstance(lines, list):
                continue
            for tier_idx, tier_raw in enumerate(lines):
                if not isinstance(tier_raw, dict):
                    continue
                tier = tier_idx + 1  # 1-based
                ctu_raw = tier_raw.get("countToUnlock", 0)
                try:
                    ctu = int(ctu_raw)
                except (TypeError, ValueError):
                    ctu = 0
                tiers_out.append(FactionLawTierRecord(
                    faction=faction, tier=tier, count_to_unlock=ctu,
                ))
                groups = tier_raw.get("groups") or ()
                for group_idx, group in enumerate(groups):
                    if not isinstance(group, dict):
                        continue
                    side = "faction" if group_idx == 0 else "army"
                    laws_in_group = group.get("laws") or ()
                    for slot, law_id in enumerate(laws_in_group):
                        if not isinstance(law_id, str):
                            continue
                        placement[law_id] = (faction, tier)
                        positions.append(LawTreePositionRecord(
                            faction=faction, tier=tier, side=side,
                            slot=slot, law_id=law_id,
                        ))
    positions.sort(key=lambda p: (p.faction, p.tier, p.side, p.slot))
    tiers_out.sort(key=lambda t: (t.faction, t.tier))
    return placement, positions, tiers_out


def extract_laws(paths: CorePaths) -> LawExtractionResult:
    """Walk DB/fractions_laws/ + DB/fractions/ and return all law-related
    records. Production laws (fractions_laws_table_<faction>.json) get
    faction + tier populated from the matching faction tree; test laws
    get null faction/tier."""
    placement, positions, tiers = _walk_faction_trees(paths)

    laws: list[LawRecord] = []
    laws_root = paths.db / "fractions_laws"
    for fp in sorted(laws_root.glob("*.json")):
        rel = fp.relative_to(paths.core_root).as_posix()
        is_prod = bool(_PROD_FILE_RE.match(fp.name))
        is_test = bool(_TEST_FILE_RE.match(fp.name))
        if not (is_prod or is_test):
            continue
        doc = load_json(fp)
        for raw in iter_array(doc):
            if not isinstance(raw, dict):
                continue
            law_id = raw.get("id")
            if not isinstance(law_id, str):
                continue
            faction, tier = (None, None)
            if is_prod:
                faction, tier = placement.get(law_id, (None, None))
            law = _build_law(
                raw, source_path=rel, is_test=is_test,
                faction=faction, tier=tier,
            )
            if law is not None:
                laws.append(law)
    laws.sort(key=lambda law: (law.test, law.faction or "", law.ordinal, law.id))
    return LawExtractionResult(
        laws=tuple(laws),
        tree_positions=tuple(positions),
        faction_tiers=tuple(tiers),
    )
