"""Per-spell wikitext page renderer.

Per D-030 (revised): each ``Data:Spell/<id>`` page carries a
``{{SpellDef}}`` row and 4 inline ``{{SpellRankDef | spell_id=<id>
| level=N | …}}`` rows. Hero-dependent placeholders (Spellpower /
hero stat refs) intentionally remain as ``{N}`` markers since the
actual values vary by caster.

Each ``SpellRankDef`` row is self-contained: it carries the English
description + bonus_description (the level-unlock blurb) inline, plus
15 × (name, desc, bonus_description) language columns. This is the
"expanded EntryDef" shape — the old ``SpellRankTranslationDef``
sibling table was folded back into ``SpellRankDef`` because the
three-translatable-field shape didn't fit the generic ``EntryDef``
name+desc-only schema.
"""

from __future__ import annotations

from typing import Any

from obelisk.emit.cargo import render_call
from obelisk.emit.unit import (
    LANG_CODE,
    _TRANSLATION_LANG_ORDER,
    _lookup_text,
)
from obelisk.models.localization import LocalizationCorpus
from obelisk.models.spell import SpellRankRecord, SpellRecord
from obelisk.resolve import PlaceholderResolver


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


def _spell_rank_field_order() -> tuple[str, ...]:
    """Field order for the merged ``{{SpellRankDef | …}}``.

    Identity (spell_id, level) → SIDs (name + desc + bonus) →
    English defaults → numeric costs → 15 × (lang_name, lang_desc,
    lang_bonus_description) triples.
    """
    base = (
        "spell_id", "level",
        "name_sid",
        "description_sid", "description",
        "bonus_description_sid", "bonus_description",
        "mana_cost", "upgrade_cost",
    )
    lang_cols: list[str] = []
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        lang_cols.extend([
            f"{code}_name", f"{code}_desc", f"{code}_bonus_description",
        ])
    return base + tuple(lang_cols)


_SPELL_RANK_FIELD_ORDER: tuple[str, ...] = _spell_rank_field_order()


def _render_rank(
    rank: SpellRankRecord,
    spell: SpellRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> str:
    """Render one merged ``{{SpellRankDef | …}}`` row.

    Combines what used to be two rows (``SpellRankDef`` for English +
    mechanical data; ``SpellRankTranslationDef`` for 15 non-English
    locales). Per-rank ``magic_json`` context ({"raw": spell.raw_json,
    "level": rank.level}) drives the resolver so per-mastery-level
    magicDealer values substitute in all 16 languages identically.
    SP-dependent placeholders (``{N}`` referencing hero stats) still
    stay unsubstituted — those resolve at display time.
    """
    magic_json = (
        {"raw": spell.raw_json, "level": rank.level}
        if spell.raw_json else None
    )

    def text(sid: str | None, lang: str) -> str | None:
        return _lookup_text(
            sid, lang, corpus, resolver, None, None,
            magic_json=magic_json,
        )

    params: dict[str, Any] = {
        "spell_id": rank.spell_id,
        "level": rank.level,
        "name_sid": spell.name_sid,
        "description_sid": rank.description_sid,
        "description": text(rank.description_sid, "english"),
        "bonus_description_sid": rank.bonus_description_sid,
        "bonus_description": text(rank.bonus_description_sid, "english"),
        "mana_cost": rank.mana_cost,
        "upgrade_cost": rank.upgrade_cost,
    }
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        if spell.name_sid:
            params[f"{code}_name"] = text(spell.name_sid, lang_dir)
        if rank.description_sid:
            params[f"{code}_desc"] = text(rank.description_sid, lang_dir)
        if rank.bonus_description_sid:
            params[f"{code}_bonus_description"] = text(
                rank.bonus_description_sid, lang_dir,
            )
    return render_call("SpellRankDef", params, key_order=_SPELL_RANK_FIELD_ORDER)


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
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        render_call("SpellDef", main_params, key_order=_SPELL_FIELD_ORDER),
    ]
    # Per D-030 (revised): no per-spell {{TranslationDef}} row, and no
    # separate per-rank translation row either — the merged
    # SpellRankDef carries name + desc + bonus_description in all 16
    # languages on a single row per (spell, level).
    for rank in spell.ranks:
        blocks.append(_render_rank(rank, spell, corpus, resolver))
    return "\n\n".join(blocks) + "\n"
