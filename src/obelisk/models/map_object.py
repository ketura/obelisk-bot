"""Canonical MapObject model.

Per D-035: one row per adventure-map structure pulled from
``DB/objects_logic/<category>/*.json``. The source data is highly
heterogeneous — chests carry loot tables, hires carry unit-data
blocks, mines carry resource arrays, etc. — but this first pass
captures only the universal display + scalar fields plus a
``source_path`` pointer so editors can dig into the raw JSON for
specifics.

Categories deliberately excluded: ``cities`` (modeled as Building),
``items`` (Artifact placement metadata), ``blocks``/``todo`` (terrain
+ dev), ``random_hires``/``unit_upgrades``/``town_gates``/
``win_condition_objects`` (generation/AI/campaign helpers).
``DB/field_objects/`` (obstacles, sentries, traps) is a separate
work item.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from obelisk.models.common import Sid


class MapObjectRecord(BaseModel):
    """One adventure-map object."""

    model_config = ConfigDict(frozen=True)

    id: str
    category: str  # source folder name under DB/objects_logic/

    # Identity / display.
    name_sid: Sid | None = None
    desc_sid: Sid | None = None
    narrative_desc_sid: Sid | None = None

    # Universal scalars (sparse — only populated when present in source).
    goods_value: int | None = None
    ai_value: int | None = None
    custom_guard_value: int | None = None
    view_radius: int | None = None
    ai_ignore: bool | None = None

    # Combat: who guards the object on the map. Stored as
    # ``<unit_sid>:<amount>`` strings to round-trip into a Cargo
    # ``List (,) of String`` column at emit time.
    guard_units: tuple[str, ...] = ()

    # Category-specific scalars (sparse).
    fraction: str | None = None        # hires faction membership
    tier: int | None = None            # hires tier (1-7)
    resource_name: str | None = None   # res_mines / res producing-resource
    resource_value: int | None = None  # res_mines daily production amount

    source_path: str


class MapObjectExtractionResult(BaseModel):
    """All map-object rows produced from a single patch extract."""

    model_config = ConfigDict(frozen=True)

    map_objects: tuple[MapObjectRecord, ...]
