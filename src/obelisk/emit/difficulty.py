"""Per-Difficulty wikitext page renderer.

Per D-039: each ``Data:Difficulty/<id>`` page carries a single
``{{Difficulty}}`` row. No Translation block — the source data
ships its name/description in English only (nameSid doesn't
resolve in any L10n file, and descriptionSid carries literal
English text rather than a key).
"""

from __future__ import annotations

from typing import Any

from obelisk.emit.cargo import render_call
from obelisk.models.difficulty import DifficultyRecord


_DIFFICULTY_FIELD_ORDER: tuple[str, ...] = (
    "id", "name_sid", "description",
    "neutral_power_multiplier",
    "player_gold", "player_wood", "player_ore",
    "player_gemstones", "player_crystals", "player_mercury", "player_dust",
    "ai_gold", "ai_wood", "ai_ore",
    "ai_gemstones", "ai_crystals", "ai_mercury", "ai_dust",
    "source_path",
)


def emit_difficulty_page(diff: DifficultyRecord) -> str:
    """Render ``Data:Difficulty/<id>``."""
    params: dict[str, Any] = {
        "id": diff.id,
        "name_sid": diff.name_sid,
        "description": diff.description,
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
    return "\n\n".join(blocks) + "\n"
