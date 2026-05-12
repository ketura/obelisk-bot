"""Per-item-set wikitext page renderer.

Per D-032: each ``Data:ItemSet/<id>`` page carries an
``{{ItemSet}}`` row, a ``{{Translation | type=item_set}}`` row for
the set name, and per-tier blocks: ``{{ItemSetTier}}`` row +
``{{Translation | type=item_set_tier}}`` row (desc-only) + N
``{{Bonus | parent_type=item_set_tier | …}}`` rows.
"""

from __future__ import annotations

from typing import Any

from obelisk.emit.cargo import render_call
from obelisk.emit.hero import render_bonus
from obelisk.emit.unit import (
    _lookup_text,
    render_translation_block,
)
from obelisk.models.item_set import (
    ItemSetRecord,
    ItemSetTierRecord,
)
from obelisk.models.localization import LocalizationCorpus
from obelisk.resolve import PlaceholderResolver


_ITEM_SET_FIELD_ORDER: tuple[str, ...] = (
    "id", "name", "name_sid", "items_in_set", "source_path",
)

_ITEM_SET_TIER_FIELD_ORDER: tuple[str, ...] = (
    "id", "set_id", "ordinal", "required_amount",
    "description_sid", "description",
)


def _render_tier(
    tier: ItemSetTierRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
    set_json: dict[str, Any] | None,
) -> list[str]:
    """Render one tier as: tier row + tier-desc Translation row + N
    Bonus rows. Returns a list of pre-rendered block strings to
    splice into the parent page's blocks list. ``set_json`` is the
    {{"config": <raw>}}-wrapped set dict so CurrentItemSet paths
    resolve in tier descriptions.
    """
    en_desc = _lookup_text(
        tier.description_sid, "english", corpus, resolver, None, None,
        set_json=set_json,
    )
    tier_params: dict[str, Any] = {
        "id": tier.id,
        "set_id": tier.set_id,
        "ordinal": tier.ordinal,
        "required_amount": tier.required_amount,
        "description_sid": tier.description_sid,
        "description": en_desc,
    }
    out: list[str] = [
        render_call("ItemSetTierDef", tier_params, key_order=_ITEM_SET_TIER_FIELD_ORDER),
    ]
    xlat = render_translation_block(
        translation_type="item_set_tier",
        target_id=tier.id,
        name_sid=None,  # tiers have no name, just a description
        desc_sid=tier.description_sid,
        corpus=corpus,
        resolver=resolver,
        set_json=set_json,
    )
    if xlat:
        out.append(xlat)
    for b in tier.bonuses:
        out.append(render_bonus(b))
    return out


def emit_item_set_page(
    item_set: ItemSetRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:ItemSet/<id>``."""
    # CurrentItemSet script reads paths like
    # "config.bonuses[N].heroBonuses[M].parameters[K]" — wrap the raw
    # set dict under a "config" key so those paths resolve naturally.
    set_json = {"config": item_set.raw_json} if item_set.raw_json else None

    en_name = _lookup_text(
        item_set.name_sid, "english", corpus, resolver, None, None,
        set_json=set_json,
    )

    main_params: dict[str, Any] = {
        "id": item_set.id,
        "name": en_name,
        "name_sid": item_set.name_sid,
        "items_in_set": ",".join(item_set.items_in_set) if item_set.items_in_set else None,
        "source_path": item_set.source_path,
    }

    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        render_call("ItemSetDef", main_params, key_order=_ITEM_SET_FIELD_ORDER),
    ]
    name_xlat = render_translation_block(
        translation_type="item_set",
        target_id=item_set.id,
        name_sid=item_set.name_sid,
        desc_sid=None,
        corpus=corpus,
        resolver=resolver,
        set_json=set_json,
    )
    if name_xlat:
        blocks.append(name_xlat)
    for tier in item_set.tiers:
        blocks.extend(_render_tier(tier, corpus, resolver, set_json))
    return "\n\n".join(blocks) + "\n"
