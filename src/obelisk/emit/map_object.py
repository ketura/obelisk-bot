"""Per-MapObject wikitext page renderer.

Per D-035: each ``Data:MapObject/<id>`` page carries a
``{{MapObject}}`` row plus a ``{{Translation | type=map_object | …}}``
row when name/desc SIDs are available. ~28 of the ~118 rows have
no name SID (single-instance specials like `tavern`, `outposts`,
etc.); those skip the Translation block entirely.
"""

from __future__ import annotations

from typing import Any

from obelisk.emit.cargo import render_call
from obelisk.emit.unit import (
    _lookup_text,
    render_translation_block,
)
from obelisk.models.localization import LocalizationCorpus
from obelisk.models.map_object import MapObjectRecord
from obelisk.resolve import PlaceholderResolver


_MAP_OBJECT_FIELD_ORDER: tuple[str, ...] = (
    "id", "category",
    "name", "name_sid",
    "desc", "desc_sid",
    "narrative_desc", "narrative_desc_sid",
    "goods_value", "ai_value", "custom_guard_value",
    "view_radius", "ai_ignore",
    "guard_units",
    "fraction", "tier",
    "resource_name", "resource_value",
    "source_path",
)


def emit_map_object_page(
    obj: MapObjectRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:MapObject/<id>``."""
    en_name = _lookup_text(
        obj.name_sid, "english", corpus, resolver, None, None,
    ) if obj.name_sid else None
    en_desc = _lookup_text(
        obj.desc_sid, "english", corpus, resolver, None, None,
    ) if obj.desc_sid else None
    en_narr = _lookup_text(
        obj.narrative_desc_sid, "english", corpus, resolver, None, None,
    ) if obj.narrative_desc_sid else None

    main_params: dict[str, Any] = {
        "id": obj.id,
        "category": obj.category,
        "name": en_name,
        "name_sid": obj.name_sid,
        "desc": en_desc,
        "desc_sid": obj.desc_sid,
        "narrative_desc": en_narr,
        "narrative_desc_sid": obj.narrative_desc_sid,
        "goods_value": obj.goods_value,
        "ai_value": obj.ai_value,
        "custom_guard_value": obj.custom_guard_value,
        "view_radius": obj.view_radius,
        "ai_ignore": obj.ai_ignore,
        "guard_units": ",".join(obj.guard_units) if obj.guard_units else None,
        "fraction": obj.fraction,
        "tier": obj.tier,
        "resource_name": obj.resource_name,
        "resource_value": obj.resource_value,
        "source_path": obj.source_path,
    }

    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        render_call("MapObject", main_params, key_order=_MAP_OBJECT_FIELD_ORDER),
    ]

    xlat = render_translation_block(
        translation_type="map_object",
        target_id=obj.id,
        name_sid=obj.name_sid,
        desc_sid=obj.desc_sid,
        corpus=corpus,
        resolver=resolver,
    )
    if xlat:
        blocks.append(xlat)

    return "\n\n".join(blocks) + "\n"
