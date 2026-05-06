"""Item set extraction.

Walks ``DB/items/item_sets/item_sets.json`` (single file, 24
records). Per D-032: nested ``bonuses[].heroBonuses[]`` source
structure unpacks into ItemSetTier rows + Bonus rows in the
unified Bonus table.
"""

from __future__ import annotations

from typing import Any

from obelisk.extract.hero import build_bonus
from obelisk.extract.loader import CorePaths, iter_array, load_json
from obelisk.models.hero import Bonus
from obelisk.models.item_set import (
    ItemSetExtractionResult,
    ItemSetRecord,
    ItemSetTierRecord,
)


def _build_tier(
    raw: dict[str, Any],
    *,
    set_id: str,
    ordinal: int,
) -> ItemSetTierRecord | None:
    """Map one source tier ({requiredItemsAmount, desc, heroBonuses[]})
    to ItemSetTierRecord. heroBonuses become Bonus rows with
    parent_type='item_set_tier' and parent_id=<tier_id>."""
    desc_sid = raw.get("desc")
    if not isinstance(desc_sid, str):
        return None
    req_raw = raw.get("requiredItemsAmount")
    try:
        required_amount = int(req_raw)
    except (TypeError, ValueError):
        return None
    tier_id = f"{set_id}_tier_{ordinal}"

    bonuses: list[Bonus] = []
    for i, b in enumerate(raw.get("heroBonuses") or ()):
        if isinstance(b, dict):
            bonus = build_bonus(b, parent_type="item_set_tier",
                                parent_id=tier_id, ordinal=i)
            if bonus is not None:
                bonuses.append(bonus)

    return ItemSetTierRecord(
        id=tier_id,
        set_id=set_id,
        ordinal=ordinal,
        required_amount=required_amount,
        description_sid=desc_sid,
        bonuses=tuple(bonuses),
    )


def _build_set(raw: dict[str, Any], source_path: str) -> ItemSetRecord | None:
    set_id = raw.get("id")
    if not isinstance(set_id, str):
        return None
    items_in_set = tuple(
        str(i) for i in (raw.get("itemsInSet") or ())
        if isinstance(i, str)
    )
    tiers: list[ItemSetTierRecord] = []
    for ordinal, tier_raw in enumerate(raw.get("bonuses") or ()):
        if isinstance(tier_raw, dict):
            tier = _build_tier(tier_raw, set_id=set_id, ordinal=ordinal)
            if tier is not None:
                tiers.append(tier)
    return ItemSetRecord(
        id=set_id,
        name_sid=str(raw.get("name", "")),
        items_in_set=items_in_set,
        tiers=tuple(tiers),
        source_path=source_path,
        raw_json=raw,
    )


def extract_item_sets(paths: CorePaths) -> ItemSetExtractionResult:
    """Walk ``DB/items/item_sets/*.json`` (one file: ``item_sets.json``)
    and return all ItemSetRecord entries. See D-032."""
    out: list[ItemSetRecord] = []
    for p in sorted((paths.db / "items" / "item_sets").glob("*.json")):
        rel = p.relative_to(paths.core_root).as_posix()
        doc = load_json(p)
        for raw in iter_array(doc):
            if not isinstance(raw, dict):
                continue
            item_set = _build_set(raw, source_path=rel)
            if item_set is not None:
                out.append(item_set)
    out.sort(key=lambda s: s.id)
    return ItemSetExtractionResult(item_sets=tuple(out))
