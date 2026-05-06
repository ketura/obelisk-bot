"""Per-spell wikitext page renderer.

Per D-030: each ``Data:Spell/<id>`` page carries a ``{{Spell}}`` row,
a ``{{Translation | type=spell | …}}`` row, and 4 inline
``{{SpellRank | spell_id=<id> | level=N | …}}`` rows. Hero-dependent
placeholders (Spellpower / hero stat refs) intentionally remain as
``{N}`` markers since the actual values vary by caster.
"""

from __future__ import annotations

from typing import Any

from artificer.emit.cargo import render_call
from artificer.emit.unit import (
    LANG_CODE,
    _TRANSLATION_LANG_ORDER,
    _lookup_text,
)
from artificer.models.localization import LocalizationCorpus
from artificer.models.spell import SpellRankRecord, SpellRecord
from artificer.resolve import PlaceholderResolver


_SPELL_FIELD_ORDER: tuple[str, ...] = (
    "id", "name", "name_sid",
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

_SPELL_RANK_FIELD_ORDER: tuple[str, ...] = (
    "spell_id", "level",
    "description_sid", "description",
    "mana_cost",
    "bonus_description_sid", "bonus_description",
    "upgrade_cost",
)


def _spell_rank_translation_field_order() -> tuple[str, ...]:
    """Field order for {{SpellRankTranslation | …}}. Carries 3 SID
    columns (name + desc + bonus_description) and 15 × 3 lang
    columns (per-language name/desc/bonus_desc triples). English
    defaults sit on Spell.name and SpellRank.description /
    SpellRank.bonus_description.
    """
    base = (
        "spell_id", "level",
        "name_sid", "desc_sid", "bonus_description_sid",
    )
    lang_cols: list[str] = []
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        lang_cols.extend([
            f"{code}_name", f"{code}_desc", f"{code}_bonus_description",
        ])
    return base + tuple(lang_cols)


_SPELL_RANK_TRANSLATION_FIELD_ORDER: tuple[str, ...] = _spell_rank_translation_field_order()


def _render_rank(
    rank: SpellRankRecord,
    spell: SpellRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> str:
    """Render one {{SpellRank | …}} row. Builds a per-rank magic_json
    context ({"raw": spell.raw_json, "level": rank.level}) so the
    interpreter's CurrentMagicBattle / CurrentMagicWorld ops index
    the correct mastery-level sub-block. SP-dependent {N} still
    stays unsubstituted."""
    magic_json = (
        {"raw": spell.raw_json, "level": rank.level}
        if spell.raw_json else None
    )
    description = _lookup_text(
        rank.description_sid, "english", corpus, resolver, None, None,
        magic_json=magic_json,
    )
    bonus_description = _lookup_text(
        rank.bonus_description_sid, "english", corpus, resolver, None, None,
        magic_json=magic_json,
    )
    params: dict[str, Any] = {
        "spell_id": rank.spell_id,
        "level": rank.level,
        "description_sid": rank.description_sid,
        "description": description,
        "mana_cost": rank.mana_cost,
        "bonus_description_sid": rank.bonus_description_sid,
        "bonus_description": bonus_description,
        "upgrade_cost": rank.upgrade_cost,
    }
    return render_call("SpellRank", params, key_order=_SPELL_RANK_FIELD_ORDER)


def _render_rank_translation(
    spell: SpellRecord,
    rank: SpellRankRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> str:
    """Render a {{SpellRankTranslation | …}} row carrying the 15
    non-English locales of the spell name + this rank's description +
    this rank's bonus description. Builds the per-rank magic_json
    context so localized placeholders also substitute correctly.
    """
    magic_json = (
        {"raw": spell.raw_json, "level": rank.level}
        if spell.raw_json else None
    )
    params: dict[str, Any] = {
        "spell_id": spell.id,
        "level": rank.level,
        "name_sid": spell.name_sid,
        "desc_sid": rank.description_sid,
        "bonus_description_sid": rank.bonus_description_sid,
    }
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        if spell.name_sid:
            params[f"{code}_name"] = _lookup_text(
                spell.name_sid, lang_dir, corpus, resolver, None, None,
                magic_json=magic_json,
            )
        if rank.description_sid:
            params[f"{code}_desc"] = _lookup_text(
                rank.description_sid, lang_dir, corpus, resolver, None, None,
                magic_json=magic_json,
            )
        if rank.bonus_description_sid:
            params[f"{code}_bonus_description"] = _lookup_text(
                rank.bonus_description_sid, lang_dir, corpus, resolver, None, None,
                magic_json=magic_json,
            )
    return render_call(
        "SpellRankTranslation",
        params,
        key_order=_SPELL_RANK_TRANSLATION_FIELD_ORDER,
    )


def emit_spell_page(
    spell: SpellRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:Spell/<id>``."""
    # For the spell-row name lookup, default level=1 (baseline mastery).
    name_mj = (
        {"raw": spell.raw_json, "level": 1}
        if spell.raw_json else None
    )
    en_name = _lookup_text(
        spell.name_sid, "english", corpus, resolver, None, None,
        magic_json=name_mj,
    )

    main_params: dict[str, Any] = {
        "id": spell.id,
        "name": en_name,
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
        "<!-- Bot-managed page. Edit the source in artificer-bot, not here. -->",
        render_call("Spell", main_params, key_order=_SPELL_FIELD_ORDER),
    ]
    # Per D-030 (revised): no per-spell {{Translation}} row.
    # Per-rank SpellRankTranslation rows below cover name + desc +
    # bonus_description in one place per (spell, level). Each rank
    # gets its own {raw, level} magic_json context so descriptions
    # substitute the per-mastery-level magicDealer values.
    for rank in spell.ranks:
        blocks.append(_render_rank(rank, spell, corpus, resolver))
        blocks.append(_render_rank_translation(spell, rank, corpus, resolver))
    return "\n\n".join(blocks) + "\n"
