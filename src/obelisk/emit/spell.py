"""Per-spell wikitext page renderer.

Per D-030 / D-040: each ``Data:Spell/<id>`` page carries:

# a ``{{SpellDef}}`` structural row (no inline name);
# ``{{TranslationDef | type=spell | target_id=<id>}}`` rows for the
  spell name, one per language;
# 4 ``{{SpellRankDef | spell_id=<id> | level=N}}`` structural-only
  rows — one per mastery level (1=no skill, 2=basic, 3=advanced,
  4=expert);
# for each rank, ``{{TranslationDef | type=spell_rank | target_id=<id>
  | variant=<level>}}`` rows carrying the level's ``description`` +
  ``bonus_description`` (the level-unlock blurb).

The spell's name is static across ranks, so ``spell_rank`` rows carry
no ``name`` — it lives once under ``type='spell'``. Hero-dependent
placeholders (Spellpower / hero stat refs) remain as ``{N}`` markers
since the actual values vary by caster.
"""

from __future__ import annotations

from typing import Any

from obelisk.emit.cargo import render_call
from obelisk.emit.unit import render_translation_block
from obelisk.models.localization import LocalizationCorpus
from obelisk.models.spell import SpellRankRecord, SpellRecord
from obelisk.resolve import PlaceholderResolver


_SPELL_FIELD_ORDER: tuple[str, ...] = (
    "id", "name_sid",
    "school", "rank", "used_on_map",
    "icon",
    "magic_type_description",
    "is_special_magic", "is_unique_magic", "normal_magic_sid",
    "learn_cost_gemstones", "learn_cost_crystals",
    "learn_cost_mercury", "learn_cost_star_dust",
    "excaption_in_tooltip_sid", "up_effect_description_sid",
    "use_expand_tooltip", "energy_cost", "energy_type",
    "source_path",
)


# Per D-040: SpellRank is structural-only. No ``name_sid`` (the spell's
# name is static across ranks — it lives on SpellDef), no inline text.
_SPELL_RANK_FIELD_ORDER: tuple[str, ...] = (
    "spell_id", "level",
    "description_sid", "bonus_description_sid",
    "mana_cost", "upgrade_cost",
)


def _render_rank(
    rank: SpellRankRecord,
    spell: SpellRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> str:
    """Render one ``{{SpellRankDef}}`` structural row plus its
    ``type='spell_rank'`` Translation rows.

    Per-rank ``magic_json`` context (``{"raw": spell.raw_json,
    "level": rank.level}``) drives the resolver so per-mastery-level
    magicDealer values substitute identically in all 16 languages.
    SP-dependent placeholders (``{N}`` referencing hero stats) stay
    unsubstituted — those resolve at display time. The ``spell_rank``
    Translation rows carry only ``description`` + ``bonus_description``;
    ``name`` belongs to the spell (``type='spell'``), not the rank.
    """
    magic_json = (
        {"raw": spell.raw_json, "level": rank.level}
        if spell.raw_json else None
    )
    params: dict[str, Any] = {
        "spell_id": rank.spell_id,
        "level": rank.level,
        "description_sid": rank.description_sid,
        "bonus_description_sid": rank.bonus_description_sid,
        "mana_cost": rank.mana_cost,
        "upgrade_cost": rank.upgrade_cost,
    }
    blocks: list[str] = [
        render_call("SpellRankDef", params, key_order=_SPELL_RANK_FIELD_ORDER),
    ]
    xlat = render_translation_block(
        translation_type="spell_rank",
        target_id=rank.spell_id,
        name_sid=None,
        desc_sid=rank.description_sid,
        corpus=corpus,
        variant=str(rank.level),
        bonus_desc_sid=rank.bonus_description_sid,
        resolver=resolver,
        magic_json=magic_json,
    )
    if xlat:
        blocks.append(xlat)
    return "\n\n".join(blocks)


def emit_spell_page(
    spell: SpellRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:Spell/<id>``."""
    main_params: dict[str, Any] = {
        "id": spell.id,
        "name_sid": spell.name_sid,
        "school": spell.school,
        "rank": spell.rank,
        "used_on_map": spell.used_on_map,
        "icon": spell.icon,
        "magic_type_description": spell.magic_type_description,
        "is_special_magic": spell.is_special_magic,
        "is_unique_magic": spell.is_unique_magic,
        "normal_magic_sid": spell.normal_magic_sid,
        "learn_cost_gemstones": spell.learn_cost_gemstones,
        "learn_cost_crystals": spell.learn_cost_crystals,
        "learn_cost_mercury": spell.learn_cost_mercury,
        "learn_cost_star_dust": spell.learn_cost_star_dust,
        "excaption_in_tooltip_sid": spell.excaption_in_tooltip_sid,
        "up_effect_description_sid": spell.up_effect_description_sid,
        "use_expand_tooltip": spell.use_expand_tooltip,
        "energy_cost": spell.energy_cost,
        "energy_type": spell.energy_type,
        "source_path": spell.source_path,
    }

    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        render_call("SpellDef", main_params, key_order=_SPELL_FIELD_ORDER),
    ]
    # The spell name lives in Translation under type='spell'. Default
    # level=1 (baseline mastery) for the resolver context — most spell
    # names are placeholder-free, so the context is harmless either way.
    name_mj = (
        {"raw": spell.raw_json, "level": 1}
        if spell.raw_json else None
    )
    name_xlat = render_translation_block(
        translation_type="spell",
        target_id=spell.id,
        name_sid=spell.name_sid,
        desc_sid=None,
        corpus=corpus,
        resolver=resolver,
        magic_json=name_mj,
    )
    if name_xlat:
        blocks.append(name_xlat)
    for rank in spell.ranks:
        blocks.append(_render_rank(rank, spell, corpus, resolver))
    return "\n\n".join(blocks) + "\n"
