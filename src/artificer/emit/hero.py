"""Per-hero and per-hero-class wikitext page renderers.

D-027: ``Data:HeroClass/<class_id>`` carries the 12 derived class
defaults; ``Data:Hero/<hero_id>`` carries per-hero data with sparse
class-default overrides. Both pages emit unified ``{{Translation}}``
rows (D-026) — heroes additionally emit a second translation row
with ``type=hero_motto`` for the hero's motto SID.
"""

from __future__ import annotations

from typing import Any

from artificer.emit.cargo import render_call
from artificer.emit.unit import (
    _lookup_text,
    render_translation_block,
)
from artificer.models.hero import (
    Bonus,
    HeroClassRecord,
    HeroRecord,
    HeroSpecializationRecord,
    HeroStartSquadSlot,
    HeroSubClassRecord,
)
from artificer.models.localization import LocalizationCorpus
from artificer.resolve import PlaceholderResolver


# -----------------------------------------------------------------------------
# HeroClass
# -----------------------------------------------------------------------------


_HERO_CLASS_FIELD_ORDER: tuple[str, ...] = (
    "id", "name", "desc", "name_sid", "desc_sid",
    "faction", "class_type",
    "mesh", "mount", "native_biome", "skills_roll_variant",
    "cost_gold", "start_level", "attacks_times_before",
    "view_radius", "stats_num", "magic_casts_per_round",
    "enable_tactics", "tactics_placement_size", "enable_hero_native_biome",
    "offence", "defence", "spell_power", "intelligence", "luck", "morale",
    "roll_lvl1_attack", "roll_lvl1_defense", "roll_lvl1_power", "roll_lvl1_knowledge",
    "roll_lvl24_attack", "roll_lvl24_defense", "roll_lvl24_power", "roll_lvl24_knowledge",
)


def _atb_str(atb: tuple[float, ...]) -> str | None:
    """Render attacks_times_before as a comma-joined string (sparse)."""
    if not atb:
        return None
    return ",".join(str(x) for x in atb)


def emit_hero_class_page(
    hero_class: HeroClassRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:HeroClass/<id>`` — ``{{HeroClass}}`` row plus the
    unified ``{{Translation | type=hero_class | …}}`` row.
    """
    en_name = _lookup_text(hero_class.name_sid, "english", corpus, resolver, None, None)
    en_desc = _lookup_text(hero_class.desc_sid, "english", corpus, resolver, None, None)
    s = hero_class.stats
    r = hero_class.stats_rolls

    params: dict[str, Any] = {
        "id": hero_class.id,
        "name": en_name,
        "desc": en_desc,
        "name_sid": hero_class.name_sid,
        "desc_sid": hero_class.desc_sid,
        "faction": hero_class.faction,
        "class_type": hero_class.class_type,
        "mesh": hero_class.mesh,
        "mount": hero_class.mount,
        "native_biome": hero_class.native_biome,
        "skills_roll_variant": hero_class.skills_roll_variant,
        "cost_gold": hero_class.cost_gold,
        "start_level": hero_class.start_level,
        "attacks_times_before": _atb_str(hero_class.attacks_times_before),
        "view_radius": s.view_radius,
        "stats_num": s.stats_num,
        "magic_casts_per_round": s.magic_casts_per_round,
        "enable_tactics": s.enable_tactics,
        "tactics_placement_size": s.tactics_placement_size,
        "enable_hero_native_biome": s.enable_hero_native_biome,
        "offence": s.offence,
        "defence": s.defence,
        "spell_power": s.spell_power,
        "intelligence": s.intelligence,
        "luck": s.luck,
        "morale": s.morale,
        "roll_lvl1_attack": r.lvl1_attack,
        "roll_lvl1_defense": r.lvl1_defense,
        "roll_lvl1_power": r.lvl1_power,
        "roll_lvl1_knowledge": r.lvl1_knowledge,
        "roll_lvl24_attack": r.lvl24_attack,
        "roll_lvl24_defense": r.lvl24_defense,
        "roll_lvl24_power": r.lvl24_power,
        "roll_lvl24_knowledge": r.lvl24_knowledge,
    }

    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in artificer-bot, not here. -->",
        render_call("HeroClass", params, key_order=_HERO_CLASS_FIELD_ORDER),
    ]
    xlat = render_translation_block(
        translation_type="hero_class",
        target_id=hero_class.id,
        name_sid=hero_class.name_sid,
        desc_sid=hero_class.desc_sid,
        corpus=corpus,
        resolver=resolver,
    )
    if xlat:
        blocks.append(xlat)
    return "\n\n".join(blocks) + "\n"


# -----------------------------------------------------------------------------
# Hero
# -----------------------------------------------------------------------------


_HERO_FIELD_ORDER: tuple[str, ...] = (
    "id", "name", "motto", "desc",
    "name_sid", "motto_sid", "desc_sid",
    "class_id", "faction", "class_type",
    "icon", "specialization_id",
    "source_path",
    # Inline list columns (always present, even if empty).
    # start_skills and start_skill_levels are positionally aligned.
    "start_skills", "start_skill_levels", "start_magics",
    # Sparse class-default overrides (omitted unless divergent):
    "cost_gold", "start_level", "attacks_times_before",
    "mesh", "mount", "native_biome", "skills_roll_variant",
    "view_radius", "stats_num", "magic_casts_per_round",
    "enable_tactics", "tactics_placement_size", "enable_hero_native_biome",
    "offence", "defence", "spell_power", "intelligence", "luck", "morale",
    "roll_lvl1_attack", "roll_lvl1_defense", "roll_lvl1_power", "roll_lvl1_knowledge",
    "roll_lvl24_attack", "roll_lvl24_defense", "roll_lvl24_power", "roll_lvl24_knowledge",
)


_HERO_START_SQUAD_FIELD_ORDER: tuple[str, ...] = (
    "hero_id", "variant", "slot", "unit_sid", "min", "max",
)


def _render_squad_slot(hero_id: str, slot: HeroStartSquadSlot) -> str:
    return render_call(
        "HeroStartSquad",
        {
            "hero_id": hero_id,
            "variant": slot.variant,
            "slot": slot.slot,
            "unit_sid": slot.unit_sid,
            "min": slot.min,
            "max": slot.max,
        },
        key_order=_HERO_START_SQUAD_FIELD_ORDER,
    )


def emit_hero_page(
    hero: HeroRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:Hero/<id>`` page body.

    Page layout:
    1. ``{{Hero | id=… | …}}`` — main row, sparse class overrides
       included only when the hero diverges from its HeroClass.
       ``start_skills`` and ``start_magics`` are inline as
       comma-joined SID lists.
    2. ``{{Translation | type=hero | target_id=<id> | …}}`` —
       name/description translation.
    3. ``{{Translation | type=hero_motto | target_id=<id> | …}}`` —
       motto translation (separate row to avoid schema specialization;
       see D-027).
    4. ``{{HeroStartSquad | …}}`` × N — primary + alt squad slots.
    """
    en_name = _lookup_text(hero.name_sid, "english", corpus, resolver, None, None)
    en_motto = _lookup_text(hero.motto_sid, "english", corpus, resolver, None, None)
    en_desc = _lookup_text(hero.desc_sid, "english", corpus, resolver, None, None)

    params: dict[str, Any] = {
        "id": hero.id,
        "name": en_name,
        "motto": en_motto,
        "desc": en_desc,
        "name_sid": hero.name_sid,
        "motto_sid": hero.motto_sid,
        "desc_sid": hero.desc_sid,
        "class_id": hero.class_id,
        "faction": hero.faction,
        "class_type": hero.class_type,
        "icon": hero.icon,
        "specialization_id": hero.specialization_id,
        "source_path": hero.source_path,
        # Inline parallel lists. Skill levels preserved (8/208 are
        # level 2); spell level/isLearned dropped (constant in 2026-05-03).
        "start_skills": ",".join(s for s, _ in hero.start_skills) if hero.start_skills else None,
        "start_skill_levels": ",".join(str(l) for _, l in hero.start_skills) if hero.start_skills else None,
        "start_magics": ",".join(hero.start_magics) if hero.start_magics else None,
    }

    # Sparse overrides — only present when diverging from class default.
    if hero.cost_gold_override is not None:
        params["cost_gold"] = hero.cost_gold_override
    if hero.start_level_override is not None:
        params["start_level"] = hero.start_level_override
    if hero.attacks_times_before_override is not None:
        params["attacks_times_before"] = _atb_str(hero.attacks_times_before_override)
    if hero.mesh_override is not None:
        params["mesh"] = hero.mesh_override
    if hero.mount_override is not None:
        params["mount"] = hero.mount_override
    if hero.native_biome_override is not None:
        params["native_biome"] = hero.native_biome_override
    if hero.skills_roll_variant_override is not None:
        params["skills_roll_variant"] = hero.skills_roll_variant_override
    if hero.stats_override is not None:
        s = hero.stats_override
        params.update({
            "view_radius": s.view_radius,
            "stats_num": s.stats_num,
            "magic_casts_per_round": s.magic_casts_per_round,
            "enable_tactics": s.enable_tactics,
            "tactics_placement_size": s.tactics_placement_size,
            "enable_hero_native_biome": s.enable_hero_native_biome,
            "offence": s.offence,
            "defence": s.defence,
            "spell_power": s.spell_power,
            "intelligence": s.intelligence,
            "luck": s.luck,
            "morale": s.morale,
        })
    if hero.stats_rolls_override is not None:
        r = hero.stats_rolls_override
        params.update({
            "roll_lvl1_attack": r.lvl1_attack,
            "roll_lvl1_defense": r.lvl1_defense,
            "roll_lvl1_power": r.lvl1_power,
            "roll_lvl1_knowledge": r.lvl1_knowledge,
            "roll_lvl24_attack": r.lvl24_attack,
            "roll_lvl24_defense": r.lvl24_defense,
            "roll_lvl24_power": r.lvl24_power,
            "roll_lvl24_knowledge": r.lvl24_knowledge,
        })

    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in artificer-bot, not here. -->",
        render_call("Hero", params, key_order=_HERO_FIELD_ORDER),
    ]

    name_xlat = render_translation_block(
        translation_type="hero",
        target_id=hero.id,
        name_sid=hero.name_sid,
        desc_sid=hero.desc_sid,
        corpus=corpus,
        resolver=resolver,
    )
    if name_xlat:
        blocks.append(name_xlat)

    motto_xlat = render_translation_block(
        translation_type="hero_motto",
        target_id=hero.id,
        name_sid=hero.motto_sid,
        desc_sid=None,
        corpus=corpus,
        resolver=resolver,
    )
    if motto_xlat:
        blocks.append(motto_xlat)

    for slot in hero.start_squad:
        blocks.append(_render_squad_slot(hero.id, slot))

    return "\n\n".join(blocks) + "\n"


# -----------------------------------------------------------------------------
# HeroSpecialization
# -----------------------------------------------------------------------------


_HERO_SPECIALIZATION_FIELD_ORDER: tuple[str, ...] = (
    "id", "name", "desc", "name_sid", "desc_sid", "icon", "source_path",
)

_BONUS_FIELD_ORDER: tuple[str, ...] = (
    "parent_type", "parent_id", "ordinal", "type", "parameters",
    "activation_level",
    "upgrade_increment", "upgrade_level_step",
    "receivers",
    "battle_type", "receiver_role", "receiver_allegiance",
)


def render_bonus(b: Bonus) -> str:
    """Per D-031: render one bonus row into the unified Bonus table.
    Used by hero specs, hero sub-classes, items, and any future
    entity carrying the (type, parameters, upgrade) shape."""
    params: dict[str, Any] = {
        "parent_type": b.parent_type,
        "parent_id": b.parent_id,
        "ordinal": b.ordinal,
        "type": b.type,
        "parameters": ",".join(b.parameters) if b.parameters else None,
    }
    if b.activation_level is not None:
        params["activation_level"] = b.activation_level
    if b.upgrade_increment is not None:
        params["upgrade_increment"] = b.upgrade_increment
    if b.upgrade_level_step is not None:
        params["upgrade_level_step"] = b.upgrade_level_step
    if b.receivers:
        params["receivers"] = ",".join(b.receivers)
    if b.battle_type is not None:
        params["battle_type"] = b.battle_type
    if b.receiver_role is not None:
        params["receiver_role"] = b.receiver_role
    if b.receiver_allegiance is not None:
        params["receiver_allegiance"] = b.receiver_allegiance
    return render_call("Bonus", params, key_order=_BONUS_FIELD_ORDER)


def emit_hero_specialization_page(
    spec: HeroSpecializationRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:HeroSpecialization/<id>``.

    Page layout:
    1. ``{{HeroSpecialization | id=… | name=… | desc=… | …}}`` — main row.
    2. ``{{Translation | type=hero_specialization | target_id=<id> | …}}``.
    3. N × ``{{HeroSpecializationBonus | spec_id=<id> | ordinal=N | …}}``.
    """
    sj = spec.raw_json or None
    en_name = _lookup_text(spec.name_sid, "english", corpus, resolver, None, None, spec_json=sj)
    en_desc = _lookup_text(spec.desc_sid, "english", corpus, resolver, None, None, spec_json=sj)

    main_params: dict[str, Any] = {
        "id": spec.id,
        "name": en_name,
        "desc": en_desc,
        "name_sid": spec.name_sid,
        "desc_sid": spec.desc_sid,
        "icon": spec.icon,
        "source_path": spec.source_path,
    }

    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in artificer-bot, not here. -->",
        render_call("HeroSpecialization", main_params,
                    key_order=_HERO_SPECIALIZATION_FIELD_ORDER),
    ]
    xlat = render_translation_block(
        translation_type="hero_specialization",
        target_id=spec.id,
        name_sid=spec.name_sid,
        desc_sid=spec.desc_sid,
        corpus=corpus,
        resolver=resolver,
        spec_json=sj,
    )
    if xlat:
        blocks.append(xlat)
    for b in spec.bonuses:
        blocks.append(render_bonus(b))
    return "\n\n".join(blocks) + "\n"


# -----------------------------------------------------------------------------
# HeroSubClass
# -----------------------------------------------------------------------------


_HERO_SUB_CLASS_FIELD_ORDER: tuple[str, ...] = (
    "id", "name", "desc", "name_sid", "desc_sid", "icon",
    "faction", "class_type",
    "activation_skill_1_sid", "activation_skill_1_level",
    "activation_skill_2_sid", "activation_skill_2_level",
    "activation_skill_3_sid", "activation_skill_3_level",
    "activation_skill_4_sid", "activation_skill_4_level",
    "activation_skill_5_sid", "activation_skill_5_level",
    "source_path",
)

def emit_hero_sub_class_page(
    sub_class: HeroSubClassRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:HeroSubClass/<id>``.

    Page layout:
    1. ``{{HeroSubClass | id=… | name=… | desc=… | activation_skill_1_sid=… | …}}``
       — main row with the 5 activation thresholds inline.
    2. ``{{Translation | type=hero_sub_class | target_id=<id> | …}}``.
    3. N × ``{{HeroSubClassBonus | sub_class_id=<id> | ordinal=N | …}}``.
    """
    en_name = _lookup_text(sub_class.name_sid, "english", corpus, resolver, None, None)
    en_desc = _lookup_text(sub_class.desc_sid, "english", corpus, resolver, None, None)

    main_params: dict[str, Any] = {
        "id": sub_class.id,
        "name": en_name,
        "desc": en_desc,
        "name_sid": sub_class.name_sid,
        "desc_sid": sub_class.desc_sid,
        "icon": sub_class.icon,
        "faction": sub_class.faction,
        "class_type": sub_class.class_type,
        "activation_skill_1_sid": sub_class.activation_skill_1_sid,
        "activation_skill_1_level": sub_class.activation_skill_1_level,
        "activation_skill_2_sid": sub_class.activation_skill_2_sid,
        "activation_skill_2_level": sub_class.activation_skill_2_level,
        "activation_skill_3_sid": sub_class.activation_skill_3_sid,
        "activation_skill_3_level": sub_class.activation_skill_3_level,
        "activation_skill_4_sid": sub_class.activation_skill_4_sid,
        "activation_skill_4_level": sub_class.activation_skill_4_level,
        "activation_skill_5_sid": sub_class.activation_skill_5_sid,
        "activation_skill_5_level": sub_class.activation_skill_5_level,
        "source_path": sub_class.source_path,
    }

    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in artificer-bot, not here. -->",
        render_call("HeroSubClass", main_params,
                    key_order=_HERO_SUB_CLASS_FIELD_ORDER),
    ]
    xlat = render_translation_block(
        translation_type="hero_sub_class",
        target_id=sub_class.id,
        name_sid=sub_class.name_sid,
        desc_sid=sub_class.desc_sid,
        corpus=corpus,
        resolver=resolver,
    )
    if xlat:
        blocks.append(xlat)
    for b in sub_class.bonuses:
        blocks.append(render_bonus(b))
    return "\n\n".join(blocks) + "\n"
