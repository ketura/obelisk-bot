"""Per-building wikitext page renderer.

Per D-034 (revised): wiki pages consolidate multiple Building rows
into one of two layouts:

* **Creature dwellings:** all 7 dwelling buildings × levels for a
  faction live on a single ``Data:Building/<faction>_Build_creature_dwellings``
  page (~14 Building rows).
* **All other buildings:** one page per (faction, sid), e.g.
  ``Data:Building/demon_Build_Main`` (3 rows for 3 levels) or
  ``Data:Building/demon_Build_Tavern`` (1 row).

Cargo row ids stay granular (``<faction>_<sid>_L<level>``) — only
the *page* hosting them is consolidated. Each Building row carries
its own matching ``{{Translation | type=building |
target_id=<id>}}`` block.

Building description SIDs reference scripts in
``info_city/city_building.script`` which are pure
``Text(return, "<literal>")`` returns — no special resolver context
needed (the existing args index + interpreter handle them out of
the box).
"""

from __future__ import annotations

from typing import Any, Iterable

from obelisk.emit.cargo import render_call
from obelisk.emit.unit import (
    _lookup_text,
    render_translation_block,
)
from obelisk.models.building import BuildingRecord
from obelisk.models.localization import LocalizationCorpus
from obelisk.resolve import PlaceholderResolver


_BUILDING_FIELD_ORDER: tuple[str, ...] = (
    "id", "faction", "category", "sid", "level",
    "name", "name_sid",
    "description", "desc_sid",
    "narrative_description", "narrative_desc_sid",
    "icon", "background_image",
    "is_constructed_on_start", "level_on_start", "scene_slot",
    "node_pos_x", "node_pos_y",
    "prereqs",
    "gold_cost", "wood_cost", "ore_cost", "crystals_cost",
    "gemstones_cost", "mercury_cost", "dust_cost", "graal_cost",
    "units_hire_sid", "units_weekly",
    "source_path",
)


def _render_one_building(
    building: BuildingRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> tuple[str, str | None]:
    """Render one Building row + its matching Translation row.

    Returns a (building_block, translation_block_or_None) pair.
    Caller stitches them into the page however it likes.
    """
    en_name = _lookup_text(
        building.name_sid, "english", corpus, resolver, None, None,
    )
    en_desc = _lookup_text(
        building.desc_sid, "english", corpus, resolver, None, None,
    )
    en_narr = _lookup_text(
        building.narrative_desc_sid, "english", corpus, resolver, None, None,
    ) if building.narrative_desc_sid else None

    main_params: dict[str, Any] = {
        "id": building.id,
        "faction": building.faction,
        "category": building.category,
        "sid": building.sid,
        "level": building.level,
        "name": en_name,
        "name_sid": building.name_sid,
        "description": en_desc,
        "desc_sid": building.desc_sid or None,
        "narrative_description": en_narr,
        "narrative_desc_sid": building.narrative_desc_sid,
        "icon": building.icon,
        "background_image": building.background_image,
        "is_constructed_on_start": building.is_constructed_on_start,
        "level_on_start": building.level_on_start,
        "scene_slot": building.scene_slot,
        "node_pos_x": building.node_pos_x,
        "node_pos_y": building.node_pos_y,
        "prereqs": ",".join(building.prereqs) if building.prereqs else None,
        "gold_cost": building.gold_cost,
        "wood_cost": building.wood_cost,
        "ore_cost": building.ore_cost,
        "crystals_cost": building.crystals_cost,
        "gemstones_cost": building.gemstones_cost,
        "mercury_cost": building.mercury_cost,
        "dust_cost": building.dust_cost,
        "graal_cost": building.graal_cost,
        "units_hire_sid": building.units_hire_sid,
        "units_weekly": building.units_weekly,
        "source_path": building.source_path,
    }
    building_block = render_call(
        "BuildingDef", main_params, key_order=_BUILDING_FIELD_ORDER,
    )
    xlat = render_translation_block(
        translation_type="building",
        target_id=building.id,
        name_sid=building.name_sid,
        desc_sid=building.desc_sid or None,
        corpus=corpus,
        resolver=resolver,
    )
    return building_block, (xlat or None)


def emit_building_page(
    building: BuildingRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render a single-Building page (legacy path / single-row pages)."""
    return emit_buildings_group_page([building], corpus, resolver=resolver)


def emit_buildings_group_page(
    buildings: Iterable[BuildingRecord],
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render a multi-Building page. The Building list determines what
    rows the page carries, in source order. Each row gets its own
    ``{{Building}}`` + ``{{Translation}}`` block."""
    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
    ]
    for b in buildings:
        bblock, xblock = _render_one_building(b, corpus, resolver)
        blocks.append(bblock)
        if xblock:
            blocks.append(xblock)
    return "\n\n".join(blocks) + "\n"