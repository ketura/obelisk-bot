"""Canonical Building model.

Per D-034: each (faction, building, level) triple flattens to a single
``BuildingRecord`` row. A 3-level building like ``Build_Main`` produces
three records: ``human_Build_Main_L1``, ``_L2``, ``_L3``.

Source folder is ``DB/objects_logic/cities/<faction>_city.json`` —
six files, one per faction. Each city dict carries 18 building-group
keys (mains, walls, magicGuilds, taverns, markets, graals, banks,
hires, etc.) plus a ``buildOrders`` list of AI build-order presets
which we skip.

Deliberately not extracted: ``bonusesPerLevel``,
``optionalEffectsPerLevel``, magic-guild ``rollChances``, and most
category-specific extras (wall bonuses, market trade rates,
artifact-market inventory, etc.). The dwelling fields
``units_hire_sid`` + ``units_weekly`` ARE pulled in for the
``hires`` category.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from obelisk.models.common import Sid


class BuildingRecord(BaseModel):
    """One (faction, sid, level) building row.

    Identity (id, faction, category, sid, level), per-level display
    fields (name, desc, narrative_desc, icon, background_image),
    construction-state fields populated only at level 1 (so wiki
    queries like "starts built" naturally filter on ``level=1``),
    city-screen grid position for this level, prereqs as a tuple of
    ``<sid>_L<level>`` strings (Cargo HOLDS-friendly), eight optional
    cost columns (one per resource — gold/wood/ore/crystals/gemstones/
    mercury/dust/graal), and dwelling-only ``units_hire_sid`` +
    ``units_weekly``.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    faction: str
    category: str
    sid: str
    level: int  # 1-based

    name_sid: Sid
    desc_sid: Sid
    narrative_desc_sid: Sid | None = None
    icon: str | None = None
    background_image: str | None = None

    # Construction state — only populated at level 1 (NULL on higher levels).
    is_constructed_on_start: bool | None = None
    level_on_start: int | None = None
    scene_slot: str | None = None

    # City-screen grid position for this level.
    node_pos_x: int | None = None
    node_pos_y: int | None = None

    # Prereqs as <sid>_L<level> strings (e.g. "Build_Main_L1").
    prereqs: tuple[str, ...] = ()

    # Per-resource cost columns; NULL when this resource isn't required.
    gold_cost: int | None = None
    wood_cost: int | None = None
    ore_cost: int | None = None
    crystals_cost: int | None = None
    gemstones_cost: int | None = None
    mercury_cost: int | None = None
    dust_cost: int | None = None
    graal_cost: int | None = None

    # Dwelling-only (category='hires').
    units_hire_sid: Sid | None = None
    units_weekly: int | None = None

    source_path: str


class BuildingExtractionResult(BaseModel):
    """All building rows produced from a single patch extract."""

    model_config = ConfigDict(frozen=True)

    buildings: tuple[BuildingRecord, ...]
