"""Per-faction wikitext page renderer.

Emits everything for a faction on a single ``Data:Faction/<id>`` page:

1. ``{{Faction | id=… | name=… | desc=… | icon=… | biome=… | …}}`` —
   the structural row with English defaults inline.
2. ``{{Translation | type=faction | target_id=<id> | <lang>_name=… | …}}``
   — the 15 non-English locales (per D-026).
3. 20 × ``{{Entry | type=FactionCityName | subtype=<faction>_<N> | …}}``
   — one row per city in the faction's randomization pool, in numeric
   source order. These rows write to the unified Cargo Entry table
   (see D-024) but the only wiki page that hosts them is the parent
   faction page; there are no individual ``Data:FactionCityName/…``
   pages. See D-025 (revised).
"""

from __future__ import annotations

from typing import Any

from artificer.emit.cargo import render_call
from artificer.emit.unit import (
    _lookup_text,
    render_entry_block,
    render_translation_block,
)
from artificer.models.faction import FactionRecord
from artificer.models.localization import LocalizationCorpus
from artificer.resolve import PlaceholderResolver


_FACTION_FIELD_ORDER: tuple[str, ...] = (
    "id", "name", "desc",
    "icon", "icon_faction_laws",
    "biome", "resource",
    "name_sid", "desc_sid",
    "source_path",
)


def emit_faction_page(
    faction: FactionRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
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
        "<!-- Bot-managed page. Edit the source in artificer-bot, not here. -->",
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

    return "\n\n".join(blocks) + "\n"
