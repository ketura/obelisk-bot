"""Per-AstrologistEvent wikitext page renderer.

Per D-038: each ``Data:AstrologistEvent/<id>`` page carries a
``{{AstrologistEvent}}`` row plus a
``{{Translation | type=astrologist_event | …}}`` row carrying the
name + desc in 16 languages.
"""

from __future__ import annotations

from typing import Any

from obelisk.emit.cargo import render_call
from obelisk.emit.unit import (
    _lookup_text,
    render_translation_block,
)
from obelisk.models.astrologist_event import AstrologistEventRecord
from obelisk.models.localization import LocalizationCorpus
from obelisk.resolve import PlaceholderResolver


_ASTROLOGIST_EVENT_FIELD_ORDER: tuple[str, ...] = (
    "id", "category",
    "name", "name_sid",
    "description", "desc_sid",
    "icon",
    "buff_sid",
    "roll_chance", "count_to_return",
    "source_path",
)


def emit_astrologist_event_page(
    event: AstrologistEventRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:AstrologistEvent/<id>``."""
    en_name = _lookup_text(
        event.name_sid, "english", corpus, resolver, None, None,
    )
    en_desc = (
        _lookup_text(
            event.desc_sid, "english", corpus, resolver, None, None,
        )
        if event.desc_sid else None
    )

    main_params: dict[str, Any] = {
        "id": event.id,
        "category": event.category,
        "name": en_name,
        "name_sid": event.name_sid,
        "description": en_desc,
        "desc_sid": event.desc_sid,
        "icon": event.icon,
        "buff_sid": event.buff_sid,
        "roll_chance": event.roll_chance,
        "count_to_return": event.count_to_return,
        "source_path": event.source_path,
    }

    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        render_call(
            "AstrologistEventDef", main_params,
            key_order=_ASTROLOGIST_EVENT_FIELD_ORDER,
        ),
    ]

    xlat = render_translation_block(
        translation_type="astrologist_event",
        target_id=event.id,
        name_sid=event.name_sid,
        desc_sid=event.desc_sid,
        corpus=corpus,
        resolver=resolver,
    )
    if xlat:
        blocks.append(xlat)

    return "\n\n".join(blocks) + "\n"