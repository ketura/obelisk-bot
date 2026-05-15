"""Per-Difficulty wikitext page renderer.

Per D-039 / D-040: each ``Data:Difficulty/<id>`` page carries a
``{{DifficultyDef}}`` row plus an English-only ``{{TranslationDef
| type=difficulty | …}}`` block. The source ships the difficulty's
description as literal English text — there is no SID and no other-
language data — so the description is fed through
``en_description_fallback`` and a query in any non-English language
correctly returns nothing. ``name_sid`` is carried for traceability
but doesn't resolve in any L10n file, so no ``name`` is emitted.
"""

from __future__ import annotations

from typing import Any

from obelisk.emit.cargo import render_call
from obelisk.emit.unit import render_translation_block
from obelisk.models.difficulty import DifficultyRecord
from obelisk.models.localization import LocalizationCorpus
from obelisk.resolve import PlaceholderResolver


_DIFFICULTY_FIELD_ORDER: tuple[str, ...] = (
    "id", "name_sid",
    "neutral_power_multiplier",
    "player_gold", "player_wood", "player_ore",
    "player_gemstones", "player_crystals", "player_mercury", "player_dust",
    "ai_gold", "ai_wood", "ai_ore",
    "ai_gemstones", "ai_crystals", "ai_mercury", "ai_dust",
    "source_path",
)


def emit_difficulty_page(
    diff: DifficultyRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:Difficulty/<id>``."""
    params: dict[str, Any] = {
        "id": diff.id,
        "name_sid": diff.name_sid,
        "neutral_power_multiplier": diff.neutral_power_multiplier,
        "player_gold": diff.player_gold,
        "player_wood": diff.player_wood,
        "player_ore": diff.player_ore,
        "player_gemstones": diff.player_gemstones,
        "player_crystals": diff.player_crystals,
        "player_mercury": diff.player_mercury,
        "player_dust": diff.player_dust,
        "ai_gold": diff.ai_gold,
        "ai_wood": diff.ai_wood,
        "ai_ore": diff.ai_ore,
        "ai_gemstones": diff.ai_gemstones,
        "ai_crystals": diff.ai_crystals,
        "ai_mercury": diff.ai_mercury,
        "ai_dust": diff.ai_dust,
        "source_path": diff.source_path,
    }
    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        render_call("DifficultyDef", params, key_order=_DIFFICULTY_FIELD_ORDER),
    ]
    # D-040: the difficulty's description is literal English source text
    # with no SID — fed through en_description_fallback so it lands in
    # the language='en' Translation row and nowhere else.
    xlat = render_translation_block(
        translation_type="difficulty",
        target_id=diff.id,
        name_sid=diff.name_sid,
        desc_sid=None,
        corpus=corpus,
        resolver=resolver,
        en_description_fallback=diff.description,
    )
    if xlat:
        blocks.append(xlat)
    return "\n\n".join(blocks) + "\n"
