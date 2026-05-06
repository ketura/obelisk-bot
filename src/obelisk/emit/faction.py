"""Per-faction wikitext page renderer.

Emits everything for a faction on a single ``Data:Faction/<id>`` page:

1. ``{{Faction | id=… | name=… | desc=… | icon=… | biome=… | …}}`` —
   the structural row with English defaults inline.
2. ``{{Translation | type=faction | target_id=<id> | <lang>_name=… | …}}``
   — the 15 non-English locales (per D-026).
3. 20 × ``{{Entry | type=FactionCityName | subtype=<faction>_<N> | …}}``
   — one row per city in the faction's randomization pool, in numeric
   source order. See D-025.
4. 5 × ``{{FactionLawTier | faction=… | tier=… | count_to_unlock=…}}`` —
   per-tier unlock thresholds (D-033).
5. ~30 × ``{{LawTreePosition | faction=… | tier=… | side=… | slot=… | law_id=…}}``
   — one row per law placement on this faction's law screen (D-033).
"""

from __future__ import annotations

from typing import Any

from obelisk.emit.cargo import render_call
from obelisk.emit.unit import (
    _lookup_text,
    render_entry_block,
    render_translation_block,
)
from obelisk.models.faction import FactionRecord
from obelisk.models.law import FactionLawTierRecord, LawTreePositionRecord
from obelisk.models.localization import LocalizationCorpus
from obelisk.resolve import PlaceholderResolver


_FACTION_FIELD_ORDER: tuple[str, ...] = (
    "id", "name", "desc",
    "icon", "icon_faction_laws",
    "biome", "resource",
    "name_sid", "desc_sid",
    "source_path",
)

_FACTION_LAW_TIER_FIELD_ORDER: tuple[str, ...] = (
    "faction", "tier", "count_to_unlock",
)

_LAW_TREE_POSITION_FIELD_ORDER: tuple[str, ...] = (
    "faction", "tier", "side", "slot", "law_id",
)


def emit_faction_page(
    faction: FactionRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
    *,
    law_tiers: tuple[FactionLawTierRecord, ...] = (),
    law_positions: tuple[LawTreePositionRecord, ...] = (),
) -> str:
    """Render the ``Data:Faction/<id>`` page body.

    Resolves the faction's ``name_sid`` / ``desc_sid`` for English
    defaults on the ``{{Faction}}`` row, then emits the unified
    ``{{Translation}}`` row (per D-026), then the inline city-name
    Entry rows (per D-025).
    """
    en_name = _lookup_text(faction.name_sid, "english", corpus, resolver, None, None)
    en_desc = _lookup_text(faction.desc_sid, "english", corpus, resolver, None, None)

    faction_params: dict[str, Any] = {
        "id": faction.id,
        "name": en_name,
        "desc": en_desc,
        "icon": faction.icon or None,
        "icon_faction_laws": faction.icon_faction_laws or None,
        "biome": faction.biome or None,
        "resource": faction.resource or None,
        "name_sid": faction.name_sid,
        "desc_sid": faction.desc_sid,
        "source_path": faction.source_path,
    }

    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        render_call(
            "Faction",
            faction_params,
            key_order=_FACTION_FIELD_ORDER,
        ),
    ]
    xlat = render_translation_block(
        translation_type="faction",
        target_id=faction.id,
        name_sid=faction.name_sid,
        desc_sid=faction.desc_sid,
        corpus=corpus,
        resolver=resolver,
    )
    if xlat:
        blocks.append(xlat)

    # City-name Entry rows live on this same page (no individual
    # Data:FactionCityName/… pages). Numeric source order, 1..N.
    for idx, city_sid in enumerate(faction.city_names, start=1):
        blocks.append(
            render_entry_block(
                entry_type="FactionCityName",
                subtype=f"{faction.id}_{idx}",
                name_sid=city_sid,
                desc_sid=None,
                corpus=corpus,
                resolver=resolver,
            )
        )

    # Per D-033: faction-law tree layout lives here too.
    for tier_row in law_tiers:
        if tier_row.faction != faction.id:
            continue
        blocks.append(render_call(
            "FactionLawTier",
            {
                "faction": tier_row.faction,
                "tier": tier_row.tier,
                "count_to_unlock": tier_row.count_to_unlock,
            },
            key_order=_FACTION_LAW_TIER_FIELD_ORDER,
        ))

    for pos in law_positions:
        if pos.faction != faction.id:
            continue
        blocks.append(render_call(
            "LawTreePosition",
            {
                "faction": pos.faction,
                "tier": pos.tier,
                "side": pos.side,
                "slot": pos.slot,
                "law_id": pos.law_id,
            },
            key_order=_LAW_TREE_POSITION_FIELD_ORDER,
        ))

    return "\n\n".join(blocks) + "\n"
