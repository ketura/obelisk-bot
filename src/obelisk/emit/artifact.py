"""Per-artifact wikitext page renderer.

Per D-031: each ``Data:Artifact/<id>`` page carries an ``{{Artifact}}``
row, a ``{{Translation | type=artifact | …}}`` row (per D-026), and
N inline ``{{Bonus | parent_type=artifact | parent_id=<id> | …}}`` rows.
"""

from __future__ import annotations

from typing import Any

from obelisk.emit.cargo import render_call
from obelisk.emit.hero import render_bonus
from obelisk.emit.unit import (
    _lookup_text,
    render_translation_block,
)
from obelisk.models.artifact import ArtifactRecord
from obelisk.models.localization import LocalizationCorpus
from obelisk.resolve import PlaceholderResolver


_ARTIFACT_FIELD_ORDER: tuple[str, ...] = (
    "id", "name", "description",
    "name_sid", "description_sid",
    "upgrade_description_sid", "upgrade_description",
    "narrative_description_sid", "narrative_description",
    "icon",
    "slot", "rarity", "artifact_set_id",
    "goods_value", "max_level",
    "cost_base", "cost_per_level", "reward_for_destroy",
    "is_special_item", "use_expand_tooltip",
    "can_destroy", "can_apply_bonus_always",
    "source_path",
)


def emit_artifact_page(
    artifact: ArtifactRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:Artifact/<id>``.

    CurrentItem script reads paths "level" and "config.bonuses[N]…" —
    wrap as {"config": <raw>, "level": 1} so the resolver substitutes
    the baseline (pre-upgrade) values into description placeholders.
    Higher-level variants would require a per-level emission pass; for
    now the wiki shows level-1 numbers and the upgrade_description
    spells out the per-level scaling (see D-031).
    """
    artifact_json = (
        {"config": artifact.raw_json, "level": 1}
        if artifact.raw_json else None
    )

    en_name = _lookup_text(
        artifact.name_sid, "english", corpus, resolver, None, None,
        artifact_json=artifact_json,
    )
    en_desc = _lookup_text(
        artifact.description_sid, "english", corpus, resolver, None, None,
        artifact_json=artifact_json,
    )
    en_upg = _lookup_text(
        artifact.upgrade_description_sid, "english", corpus, resolver, None, None,
        artifact_json=artifact_json,
    )
    en_narr = _lookup_text(
        artifact.narrative_description_sid, "english", corpus, resolver, None, None,
        artifact_json=artifact_json,
    )

    main_params: dict[str, Any] = {
        "id": artifact.id,
        "name": en_name,
        "description": en_desc,
        "name_sid": artifact.name_sid,
        "description_sid": artifact.description_sid,
        "upgrade_description_sid": artifact.upgrade_description_sid,
        "upgrade_description": en_upg,
        "narrative_description_sid": artifact.narrative_description_sid,
        "narrative_description": en_narr,
        "icon": artifact.icon,
        "slot": artifact.slot,
        "rarity": artifact.rarity,
        "artifact_set_id": artifact.artifact_set_id,
        "goods_value": artifact.goods_value,
        "max_level": artifact.max_level,
        "cost_base": artifact.cost_base,
        "cost_per_level": artifact.cost_per_level,
        "reward_for_destroy": artifact.reward_for_destroy,
        "is_special_item": artifact.is_special_item,
        "use_expand_tooltip": artifact.use_expand_tooltip,
        "can_destroy": artifact.can_destroy,
        "can_apply_bonus_always": artifact.can_apply_bonus_always,
        "source_path": artifact.source_path,
    }

    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        render_call("Artifact", main_params, key_order=_ARTIFACT_FIELD_ORDER),
    ]
    xlat = render_translation_block(
        translation_type="artifact",
        target_id=artifact.id,
        name_sid=artifact.name_sid,
        desc_sid=artifact.description_sid,
        corpus=corpus,
        resolver=resolver,
        artifact_json=artifact_json,
    )
    if xlat:
        blocks.append(xlat)
    for b in artifact.bonuses:
        blocks.append(render_bonus(b))
    return "\n\n".join(blocks) + "\n"
