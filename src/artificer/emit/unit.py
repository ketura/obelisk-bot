"""Per-unit wikitext page renderer."""

from __future__ import annotations

from typing import Any

from artificer.emit.cargo import block_hash, render_call
from artificer.resolve import PlaceholderResolver, html_to_wiki
from artificer.extract.ownership import OwnershipClaims
from artificer.models.localization import LocalizationCorpus
from artificer.models.unit import AttackSlot, Unit, UnitAbility, UnitAttack


RESOURCE_COLUMN: dict[str, str] = {
    "gold": "gold",
    "wood": "wood",
    "ore": "ore",
    "mercury": "mercury",
    "dust": "dust",
    "crystals": "crystal",
    "gemstones": "gemstone",
}


LANG_CODE: dict[str, str] = {
    "BRportugese": "pt_br",
    "czech": "cs",
    "english": "en",
    "french": "fr",
    "german": "de",
    "hungarian": "hu",
    "italian": "it",
    "japanese": "ja",
    "korean": "ko",
    "polish": "pl",
    "russian": "ru",
    "spanish": "es",
    "turkish": "tr",
    "ukrainian": "uk",
    "zhCN": "zh_cn",
    "zhTW": "zh_tw",
}

_TRANSLATION_LANG_ORDER: tuple[str, ...] = (
    "BRportugese", "czech", "french", "german", "hungarian",
    "italian", "japanese", "korean", "polish", "russian",
    "spanish", "turkish", "ukrainian", "zhCN", "zhTW",
)


_UNIT_FIELD_ORDER: tuple[str, ...] = (
    "id", "unused", "faction", "tier", "source_path",
    "name", "desc", "name_sid", "desc_sid", "base_sid", "upgrade_sid",
    "hp", "offence", "defence", "damage_min", "damage_max",
    "initiative", "speed", "luck", "morale",
    "energy_per_cast", "energy_per_round", "energy_per_take_damage",
    "action_points", "num_counters",
    "morale_min", "morale_max", "luck_min", "luck_max", "move_type",
    "creature_type", "immunities", "disablers", "shared_abilities",
    *(f"{c}_cost" for c in RESOURCE_COLUMN.values()),
    "native_biome", "ai_archetype", "tags", "leave_corpse",
    "squad_value", "exp_bonus",
)


_TEMPLATE_NAME_BY_TYPE: dict[str, str] = {
    "active": "ActiveAbility",
    "passive": "PassiveAbility",
    "conditional_passive": "ConditionalPassiveAbility",
    "global_passive": "GlobalPassiveAbility",
    "aura": "AuraAbility",
    "stat_passive": "StatPassiveAbility",
}


_IDENTITY_ORDER: tuple[str, ...] = (
    "ability_id", "unit_id", "ability_type", "ordinal", "variant",
    "name", "desc", "name_sid", "desc_sid",
)


_ACTIVE_ORDER: tuple[str, ...] = _IDENTITY_ORDER + (
    "attack_type", "rank", "cd", "energy_level", "action_cost", "charges",
    "disable_for_ai", "never_disable", "move_type_active",
    "use_all_energy_levels", "dont_use_energy", "untargeted_cast", "instacast",
    "attack_pattern_sid", "damage_target", "damage_type", "stat_dmg_mult",
    "trigger_counter", "multitarget_type", "num_targets",
    "dont_trigger_energy_regen", "return_to_start_after_attack",
    "min_base_dmg", "max_base_dmg", "min_stack_dmg", "max_stack_dmg",
    "min_damage_per_energy_level", "max_damage_per_energy_level",
    "damage_multipler_per_hero_level", "temp_self_buff",
    "buff_sid", "buff_target", "buff_duration", "buff_charges",
    "shoot_range", "shoot_threshold", "shoot_red_count", "shoot_dmg_buff",
    "use_speed_as_shoot_range",
    "cast_target", "cast_selection", "cast_target_condition", "cast_target_tags",
    "affect_target", "affect_selection", "affect_target_condition", "affect_target_tags",
)

_PASSIVE_ORDER: tuple[str, ...] = _IDENTITY_ORDER + ("sequence_effect",)
_CONDITIONAL_ORDER: tuple[str, ...] = _IDENTITY_ORDER + (
    "condition_check", "condition_target", "condition_value",
    "affected_stat", "affected_stat_amount",
)
_GLOBAL_ORDER: tuple[str, ...] = _IDENTITY_ORDER + (
    "global_target", "global_power", "global_tag",
    "affected_stat", "affected_stat_amount",
)
_AURA_ORDER: tuple[str, ...] = _IDENTITY_ORDER + (
    "aura_target", "aura_power", "aura_radius", "aura_tag",
    "affected_stat", "affected_stat_amount",
)
_STAT_PASSIVE_ORDER: tuple[str, ...] = _IDENTITY_ORDER + (
    "affected_stat", "affected_stat_amount",
)

_FALLBACK_ORDER: tuple[str, ...] = _IDENTITY_ORDER

_ORDER_BY_TYPE: dict[str, tuple[str, ...]] = {
    "active": _ACTIVE_ORDER,
    "passive": _PASSIVE_ORDER,
    "conditional_passive": _CONDITIONAL_ORDER,
    "global_passive": _GLOBAL_ORDER,
    "aura": _AURA_ORDER,
    "stat_passive": _STAT_PASSIVE_ORDER,
}


# ----------------------------------------------------------------------------
# UnitAttack template (D-021, revised: one row per unit)
# ----------------------------------------------------------------------------

# Per-slot field list (without the slot prefix). Each slot in a UnitAttack
# row gets these fields prefixed with its slot name (default_/counter_/
# alt_/alt2_).
_SLOT_FIELDS: tuple[str, ...] = (
    "attack_type",
    "stat_dmg_mult",
    "damage_target",
    "affect_target",
    "trigger_counter",
    "damage_type",
    "buff_sid",
    "buff_target",
    "buff_duration",
    "cd",
    "dont_use_energy",
    "return_to_start_after_attack",
    "never_disable",
    "temp_self_buff",
    "dont_trigger_energy_regen",
    "multitarget_type",
    "num_targets",
    "is_armed_ability",
)

# Defaults applied per-slot. Bot suppresses fields whose value matches.
_SLOT_DEFAULTS: dict[str, dict[str, Any]] = {
    "default": {
        "stat_dmg_mult": 1.0, "trigger_counter": True,
        "damage_target": "enemy", "affect_target": "enemy",
        "damage_type": "normal",
    },
    "counter": {
        "stat_dmg_mult": 1.0, "trigger_counter": False,
        "damage_target": "enemy", "affect_target": "enemy",
        "damage_type": "normal",
    },
    "alt": {
        "stat_dmg_mult": 0.5, "trigger_counter": False,
        "damage_target": "enemy", "affect_target": "enemy",
        "damage_type": "normal",
    },
    "alt2": {
        "stat_dmg_mult": 0.5, "trigger_counter": False,
        "damage_target": "enemy", "affect_target": "enemy",
        "damage_type": "normal",
    },
}


def _slot_to_params(prefix: str, slot: AttackSlot | None) -> dict[str, Any]:
    """Flatten an AttackSlot into a {prefix_field: value} dict, applying
    default suppression and pattern_sid omission when canonical."""
    if slot is None:
        return {}
    defaults = _SLOT_DEFAULTS.get(prefix, {})
    out: dict[str, Any] = {}

    # Pattern-passive references (``passive_id``) are intentionally NOT
    # emitted on UnitAttack — they're already tracked via the unit's
    # shared_abilities list (which carries the ``base_passive_strike_*``
    # name SIDs from views.passives). The wiki layer joins those against
    # the AttackPassive table.
    # Engine pattern_sid is also NOT emitted — wiki readers see the
    # player-facing AttackPassive name, not the engine sid.
    raw: dict[str, Any] = {
        "attack_type": slot.attack_type,
        "stat_dmg_mult": slot.stat_dmg_mult,
        "damage_target": slot.damage_target,
        "affect_target": slot.affect_target,
        "trigger_counter": slot.trigger_counter,
        "damage_type": slot.damage_type,
        "buff_sid": slot.buff_sid,
        "buff_target": slot.buff_target,
        "buff_duration": slot.buff_duration,
        "cd": slot.cd,
        "dont_use_energy": slot.dont_use_energy,
        "return_to_start_after_attack": slot.return_to_start_after_attack,
        "never_disable": slot.never_disable,
        "temp_self_buff": slot.temp_self_buff,
        "dont_trigger_energy_regen": slot.dont_trigger_energy_regen,
        "multitarget_type": slot.multitarget_type,
        "num_targets": slot.num_targets,
        "is_armed_ability": slot.is_armed_ability,
    }

    for field, value in raw.items():
        if value is None:
            continue
        if field in defaults and value == defaults[field]:
            continue
        out[f"{prefix}_{field}"] = value
    return out


def _unit_attack_field_order() -> tuple[str, ...]:
    """Compose the full field-order tuple for a UnitAttack row."""
    order: list[str] = ["unit_id"]
    for prefix in ("default", "counter", "alt", "alt2"):
        for f in _SLOT_FIELDS:
            order.append(f"{prefix}_{f}")
    return tuple(order)


_UNIT_ATTACK_FIELD_ORDER = _unit_attack_field_order()


def _unit_attack_params(record: UnitAttack) -> dict[str, Any]:
    """Build the param dict for the per-unit UnitAttack row."""
    params: dict[str, Any] = {"unit_id": record.unit_id}
    params.update(_slot_to_params("default", record.default))
    params.update(_slot_to_params("counter", record.counter))
    params.update(_slot_to_params("alt", record.alt))
    params.update(_slot_to_params("alt2", record.alt2))
    return params


# ----------------------------------------------------------------------------
# Shared AttackArchetype + AttackPassive seed-data emitters
# ----------------------------------------------------------------------------

# Hand-curated seed for the 3-row AttackArchetype reference table.
# Maps the bot's player-facing attack_type enum to the L10n SID family
# that drives display_name / description.
ATTACK_ARCHETYPE_SEEDS: dict[str, dict[str, Any]] = {
    "melee": {
        "name_sid": "base_passive_melee_attack_name",
        "desc_sid": "base_passive_melee_attack_description",
        "display_name_fallback": "Melee Attack",
    },
    "ranged": {
        "name_sid": "base_passive_ranged_attack_name",
        "desc_sid": "base_passive_ranged_attack_description",
        "display_name_fallback": "Ranged Attack",
    },
    "reach": {
        "name_sid": "base_passive_remote_attack_name",
        "desc_sid": "base_passive_remote_attack_description",
        "display_name_fallback": "Long Reach",
    },
}


_ATTACK_ARCHETYPE_FIELD_ORDER: tuple[str, ...] = (
    "attack_type", "display_name", "description", "name_sid", "desc_sid",
)


def emit_attack_archetype_page(
    attack_type: str,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:AttackArchetype/<attack_type>`` — the parent
    {{AttackArchetype | …}} call plus its {{AttackArchetypeTranslation}}
    sibling for the 15 non-English locales.
    """
    seed = ATTACK_ARCHETYPE_SEEDS[attack_type]
    name_sid = seed["name_sid"]
    desc_sid = seed["desc_sid"]

    en_name = _lookup_text(name_sid, "english", corpus, resolver, None, None)
    en_desc = _lookup_text(desc_sid, "english", corpus, resolver, None, None)

    parent_params: dict[str, Any] = {
        "attack_type": attack_type,
        "display_name": en_name or seed["display_name_fallback"],
        "description": en_desc,
        "name_sid": name_sid,
        "desc_sid": desc_sid,
    }

    translation_params: dict[str, Any] = {
        "attack_type": attack_type,
        "name_sid": name_sid,
        "desc_sid": desc_sid,
    }
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        translation_params[f"{code}_name"] = _lookup_text(
            name_sid, lang_dir, corpus, resolver, None, None
        )
        translation_params[f"{code}_desc"] = _lookup_text(
            desc_sid, lang_dir, corpus, resolver, None, None
        )
    translation_key_order = ["attack_type", "name_sid", "desc_sid"]
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        translation_key_order.extend([f"{code}_name", f"{code}_desc"])

    blocks = [
        "<!-- Bot-managed page. Edit the source in artificer-bot, not here. -->",
        render_call(
            "AttackArchetype",
            parent_params,
            key_order=_ATTACK_ARCHETYPE_FIELD_ORDER,
        ),
        render_call(
            "AttackArchetypeTranslation",
            translation_params,
            key_order=translation_key_order,
        ),
    ]
    return "\n\n".join(blocks) + "\n"


# ----------------------------------------------------------------------------
# Shared AttackPassive seed-data emitter
# ----------------------------------------------------------------------------

_ATTACK_PASSIVE_FIELD_ORDER: tuple[str, ...] = (
    "attack_passive_id", "pattern_token", "rank",
    "name_sid", "desc_sid", "display_name", "description",
)

_ATTACK_PASSIVE_TRANSLATION_FIELD_ORDER: tuple[str, ...] = (
    "attack_passive_id", "name_sid", "desc_sid",
    *(f"{LANG_CODE[d]}_name" if k == 0 else f"{LANG_CODE[d]}_desc"
      for d in _TRANSLATION_LANG_ORDER for k in (0, 1)),
)


def emit_attack_passive_page(
    attack_passive_id: str,
    info: dict[str, Any],
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:AttackPassive/<attack_passive_id>`` — one
    {{AttackPassive | …}} call (English defaults) plus one
    {{AttackPassiveTranslation | …}} call (15 non-English locales).
    """
    name_sid = info.get("name_sid")
    desc_sid = info.get("desc_sid")

    en_name = (
        _lookup_text(name_sid, "english", corpus, resolver, None, None)
        if isinstance(name_sid, str) else None
    )
    en_desc = (
        _lookup_text(desc_sid, "english", corpus, resolver, None, None)
        if isinstance(desc_sid, str) else None
    )

    parent_params: dict[str, Any] = {
        "attack_passive_id": attack_passive_id,
        "pattern_token": info.get("pattern_token"),
        "rank": info.get("rank"),
        "name_sid": name_sid,
        "desc_sid": desc_sid,
        "display_name": en_name or info.get("display_name"),
        "description": en_desc,
    }

    translation_params: dict[str, Any] = {
        "attack_passive_id": attack_passive_id,
        "name_sid": name_sid,
        "desc_sid": desc_sid,
    }
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        if isinstance(name_sid, str):
            translation_params[f"{code}_name"] = _lookup_text(
                name_sid, lang_dir, corpus, resolver, None, None
            )
        if isinstance(desc_sid, str):
            translation_params[f"{code}_desc"] = _lookup_text(
                desc_sid, lang_dir, corpus, resolver, None, None
            )

    translation_key_order = ["attack_passive_id", "name_sid", "desc_sid"]
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        translation_key_order.extend([f"{code}_name", f"{code}_desc"])

    blocks = [
        "<!-- Bot-managed page. Edit the source in artificer-bot, not here. -->",
        render_call(
            "AttackPassive",
            parent_params,
            key_order=_ATTACK_PASSIVE_FIELD_ORDER,
        ),
        render_call(
            "AttackPassiveTranslation",
            translation_params,
            key_order=translation_key_order,
        ),
    ]
    return "\n\n".join(blocks) + "\n"


def make_ability_id(
    unit_id: str, ability_type: str, ordinal: int | None, variant: str | None,
) -> str:
    """Synthetic key for a UnitAbility row."""
    parts = [unit_id]
    if ability_type and ability_type != "active":
        parts.append(ability_type)
    if ordinal is not None:
        parts.append(str(ordinal))
    if variant and variant not in ("base",):
        parts.append(variant)
    return "_".join(parts)


def emit_unit_page(
    unit: Unit,
    claims: OwnershipClaims | None,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
    unit_json: dict[str, Any] | None = None,
) -> str:
    """Render the full wikitext for ``Data:Unit/<unit.id>``."""
    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in artificer-bot, not here. -->",
        render_call("Unit", _unit_params(unit, corpus, resolver, unit_json), key_order=_UNIT_FIELD_ORDER),
    ]

    for ability in unit.unit_abilities:
        template = _TEMPLATE_NAME_BY_TYPE.get(ability.ability_type, "UnitAbility")
        order = _ORDER_BY_TYPE.get(ability.ability_type, _FALLBACK_ORDER)
        blocks.append(
            render_call(
                template,
                _ability_params(unit.id, ability, corpus, resolver, unit_json),
                key_order=order,
            )
        )

    # D-021 (revised): single per-unit UnitAttack row inline on the
    # unit page. Pattern-passives are referenced by attack_passive_id
    # against the shared AttackPassive table, not duplicated here.
    if unit.unit_attack is not None:
        blocks.append(
            render_call(
                "UnitAttack",
                _unit_attack_params(unit.unit_attack),
                key_order=_UNIT_ATTACK_FIELD_ORDER,
            )
        )

    blocks.append(_render_unit_translation(unit, corpus, resolver, unit_json))
    for ability in unit.unit_abilities:
        blocks.append(_render_ability_translation(unit.id, ability, corpus, resolver, unit_json))

    return "\n\n".join(blocks) + "\n"


def _lookup_text(
    sid: str | None, lang: str, corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None, unit_json: dict[str, Any] | None,
    ability_json: dict[str, Any] | None = None,
) -> str | None:
    if not sid:
        return None
    raw = corpus.get(sid, lang)
    if raw is None:
        return None
    if resolver is not None:
        return resolver.resolve(sid, raw, unit_json, lang=lang, ability_json=ability_json)
    return html_to_wiki(raw)


def _ability_json_for(ability: UnitAbility, unit_json: dict[str, Any] | None) -> dict[str, Any] | None:
    if unit_json is None or ability.ordinal is None:
        return None
    idx = ability.ordinal - 1
    array_key: str | None = None
    if ability.ability_type == "active":
        array_key = "abilities"
    elif ability.ability_type == "passive":
        array_key = "passives"
    elif ability.ability_type == "conditional_passive":
        array_key = "conditionalPassives"
    elif ability.ability_type == "global_passive":
        array_key = "globalPassives"
    if array_key is None:
        return None
    arr = unit_json.get(array_key)
    if not isinstance(arr, list) or idx < 0 or idx >= len(arr):
        return None
    entry = arr[idx]
    return entry if isinstance(entry, dict) else None


def _render_unit_translation(
    unit: Unit, corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None, unit_json: dict[str, Any] | None = None,
) -> str:
    params: dict[str, Any] = {
        "unit_id": unit.id,
        "name_sid": unit.name_sid,
        "desc_sid": unit.narrative_description_sid,
    }
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        params[f"{code}_name"] = _lookup_text(unit.name_sid, lang_dir, corpus, resolver, unit_json)
        if unit.narrative_description_sid:
            params[f"{code}_desc"] = _lookup_text(unit.narrative_description_sid, lang_dir, corpus, resolver, unit_json)
    key_order = ["unit_id", "name_sid", "desc_sid"]
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        key_order.extend([f"{code}_name", f"{code}_desc"])
    return render_call("UnitTranslation", params, key_order=key_order)


def _render_ability_translation(
    unit_id: str, ability: UnitAbility, corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None, unit_json: dict[str, Any] | None = None,
) -> str:
    params: dict[str, Any] = {
        "ability_id": make_ability_id(unit_id, ability.ability_type, ability.ordinal, ability.variant),
        "unit_id": unit_id,
        "ability_type": ability.ability_type,
        "ordinal": ability.ordinal,
        "variant": ability.variant,
        "name_sid": ability.name_sid,
        "desc_sid": ability.desc_sid,
    }
    aj = _ability_json_for(ability, unit_json)
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        if ability.name_sid:
            params[f"{code}_name"] = _lookup_text(ability.name_sid, lang_dir, corpus, resolver, unit_json, aj)
        if ability.desc_sid:
            params[f"{code}_desc"] = _lookup_text(ability.desc_sid, lang_dir, corpus, resolver, unit_json, aj)
    key_order = ["ability_id", "unit_id", "ability_type", "ordinal", "variant", "name_sid", "desc_sid"]
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        key_order.extend([f"{code}_name", f"{code}_desc"])
    return render_call("UnitAbilityTranslation", params, key_order=key_order)


def _unit_params(
    unit: Unit, corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None, unit_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    s = unit.stats
    cost_by_resource = {c.resource: c.amount for c in unit.cost}
    en_name = _lookup_text(unit.name_sid, "english", corpus, resolver, unit_json)
    en_desc = _lookup_text(unit.narrative_description_sid, "english", corpus, resolver, unit_json)
    params: dict[str, Any] = {
        "id": unit.id,
        "faction": unit.faction.value,
        "tier": unit.tier,
        "source_path": unit.source_path,
        "name": en_name,
        "desc": en_desc,
        "name_sid": unit.name_sid,
        "desc_sid": unit.narrative_description_sid,
        "base_sid": unit.base_sid,
        "upgrade_sid": unit.upgrade_sid,
        "hp": s.hp, "offence": s.offence, "defence": s.defence,
        "damage_min": s.damage_min, "damage_max": s.damage_max,
        "initiative": s.initiative, "speed": s.speed,
        "luck": s.luck, "morale": s.morale,
        "energy_per_cast": s.energy_per_cast,
        "energy_per_round": s.energy_per_round,
        "energy_per_take_damage": s.energy_per_take_damage,
        "action_points": s.action_points,
        "num_counters": s.num_counters,
        "morale_min": s.morale_min, "morale_max": s.morale_max,
        "luck_min": s.luck_min, "luck_max": s.luck_max,
        "move_type": s.move_type,
        "creature_type": unit.creature_type,
        "immunities": list(unit.immunities),
        "disablers": list(unit.disablers),
        "shared_abilities": list(unit.shared_abilities),
    }
    for source_name, column_base in RESOURCE_COLUMN.items():
        params[f"{column_base}_cost"] = cost_by_resource.get(source_name)
    params.update({
        "native_biome": unit.native_biome,
        "ai_archetype": unit.ai_archetype,
        "tags": list(unit.tags),
        "leave_corpse": unit.leave_corpse,
        "squad_value": unit.squad_value,
        "exp_bonus": unit.exp_bonus,
    })
    if unit.unused:
        params["unused"] = True
    return params


def _ability_params(
    unit_id: str, ability: UnitAbility, corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None, unit_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    aj = _ability_json_for(ability, unit_json)
    en_name = _lookup_text(ability.name_sid, "english", corpus, resolver, unit_json, aj) if ability.name_sid else None
    en_desc = _lookup_text(ability.desc_sid, "english", corpus, resolver, unit_json, aj) if ability.desc_sid else None
    return {
        "ability_id": make_ability_id(unit_id, ability.ability_type, ability.ordinal, ability.variant),
        "unit_id": unit_id,
        "ability_type": ability.ability_type,
        "ordinal": ability.ordinal,
        "variant": ability.variant,
        "name": en_name,
        "desc": en_desc,
        "name_sid": ability.name_sid,
        "desc_sid": ability.desc_sid,
        "affected_stat": ability.affected_stat,
        "affected_stat_amount": ability.affected_stat_amount,
        "attack_type": ability.attack_type,
        "rank": ability.rank,
        "cd": ability.cd,
        "energy_level": ability.energy_level,
        "action_cost": ability.action_cost,
        "charges": ability.charges,
        "disable_for_ai": ability.disable_for_ai,
        "never_disable": ability.never_disable,
        "move_type_active": ability.move_type_active,
        "use_all_energy_levels": ability.use_all_energy_levels,
        "dont_use_energy": ability.dont_use_energy,
        "untargeted_cast": ability.untargeted_cast,
        "instacast": ability.instacast,
        "attack_pattern_sid": ability.attack_pattern_sid,
        "damage_target": ability.damage_target,
        "damage_type": ability.damage_type,
        "stat_dmg_mult": ability.stat_dmg_mult,
        "trigger_counter": ability.trigger_counter,
        "multitarget_type": ability.multitarget_type,
        "num_targets": ability.num_targets,
        "dont_trigger_energy_regen": ability.dont_trigger_energy_regen,
        "return_to_start_after_attack": ability.return_to_start_after_attack,
        "min_base_dmg": ability.min_base_dmg,
        "max_base_dmg": ability.max_base_dmg,
        "min_stack_dmg": ability.min_stack_dmg,
        "max_stack_dmg": ability.max_stack_dmg,
        "min_damage_per_energy_level": ability.min_damage_per_energy_level,
        "max_damage_per_energy_level": ability.max_damage_per_energy_level,
        "damage_multipler_per_hero_level": ability.damage_multipler_per_hero_level,
        "temp_self_buff": ability.temp_self_buff,
        "buff_sid": ability.buff_sid,
        "buff_target": ability.buff_target,
        "buff_duration": ability.buff_duration,
        "buff_charges": ability.buff_charges,
        "shoot_range": ability.shoot_range,
        "shoot_threshold": ability.shoot_threshold,
        "shoot_red_count": ability.shoot_red_count,
        "shoot_dmg_buff": ability.shoot_dmg_buff,
        "use_speed_as_shoot_range": ability.use_speed_as_shoot_range,
        "cast_target": ability.cast_target,
        "cast_selection": ability.cast_selection,
        "cast_target_condition": ability.cast_target_condition,
        "cast_target_tags": list(ability.cast_target_tags),
        "affect_target": ability.affect_target,
        "affect_selection": ability.affect_selection,
        "affect_target_condition": ability.affect_target_condition,
        "affect_target_tags": list(ability.affect_target_tags),
        "condition_check": ability.condition_check,
        "condition_target": ability.condition_target,
        "condition_value": ability.condition_value,
        "global_target": ability.global_target,
        "global_power": ability.global_power,
        "global_tag": ability.global_tag,
        "aura_target": ability.aura_target,
        "aura_power": ability.aura_power,
        "aura_radius": ability.aura_radius,
        "aura_tag": ability.aura_tag,
        "sequence_effect": ability.sequence_effect,
    }


# end-of-module sync sentinel
