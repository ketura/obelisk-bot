"""Per-unit wikitext page renderer."""

from __future__ import annotations

from typing import Any, Iterator

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
# Shared Entry seed-data emitter (unified reference table per D-024)
# ----------------------------------------------------------------------------

# Hand-curated seed for the unified Entry reference table. Top-level
# keys are Entry `type` values; their values map `subtype` -> info dict
# with the L10n SIDs that drive display_name/description plus an English
# fallback. Optional `icon` field per entry. See D-024.
ENTRY_SEEDS: dict[str, dict[str, dict[str, Any]]] = {
    "attack_archetype": {
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
    },
    "movement": {
        "fly": {
            "name_sid": "base_passive_flyer_name",
            "desc_sid": "base_passive_flyer_description",
            "display_name_fallback": "Flying",
        },
        "teleport": {
            "name_sid": "base_passive_blink_name",
            "desc_sid": "base_passive_blink_description",
            # Display-name flip: 'teleport' enum → "Blink" in-game.
            "display_name_fallback": "Blink",
        },
    },
    "creature_type": {
        "living": {
            "name_sid": "base_class_living",
            "desc_sid": "base_class_living_description",
            "display_name_fallback": "Living",
        },
        "undead": {
            "name_sid": "base_class_undead",
            "desc_sid": "base_class_undead_description",
            "display_name_fallback": "Undead",
        },
        "demon": {
            "name_sid": "base_class_demon",
            "desc_sid": "base_class_demon_description",
            # Display-name flip: 'demon' enum → "Hive Spawn" in-game.
            "display_name_fallback": "Hive Spawn",
        },
        "magic_creature": {
            "name_sid": "base_class_magic_creature",
            "desc_sid": "base_class_magic_creature_description",
            "display_name_fallback": "Magic Creature",
        },
        "embodiment": {
            "name_sid": "base_class_embodiment",
            "desc_sid": "base_class_embodiment_description",
            "display_name_fallback": "Embodiment",
        },
        "dragon": {
            "name_sid": "base_class_dragon",
            "desc_sid": "base_class_dragon_description",
            "display_name_fallback": "Dragon",
        },
        "construct": {
            "name_sid": "base_class_construct",
            "desc_sid": "base_class_construct_description",
            "display_name_fallback": "Construct",
        },
    },
}


def _entry_field_order() -> tuple[str, ...]:
    base = ("type", "subtype", "display_name", "description", "icon",
            "name_sid", "desc_sid")
    lang_pairs: list[str] = []
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        lang_pairs.extend([f"{code}_name", f"{code}_desc"])
    return base + tuple(lang_pairs)


_ENTRY_FIELD_ORDER: tuple[str, ...] = _entry_field_order()


def _translation_field_order() -> tuple[str, ...]:
    """Field order for ``{{Translation | …}}`` invocations.

    Per D-026: type and target_id at the head, then the SID pair for
    traceability, then 15 × (lang_name, lang_desc) pairs in
    `_TRANSLATION_LANG_ORDER`.
    """
    base = ("type", "target_id", "name_sid", "desc_sid")
    lang_pairs: list[str] = []
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        lang_pairs.extend([f"{code}_name", f"{code}_desc"])
    return base + tuple(lang_pairs)


_TRANSLATION_FIELD_ORDER: tuple[str, ...] = _translation_field_order()


def render_translation_block(
    translation_type: str,
    target_id: str,
    name_sid: str | None,
    desc_sid: str | None,
    corpus: LocalizationCorpus,
    *,
    resolver: PlaceholderResolver | None = None,
    unit_json: dict[str, Any] | None = None,
    ability_json: dict[str, Any] | None = None,
    spec_json: dict[str, Any] | None = None,
    magic_json: dict[str, Any] | None = None,
    set_json: dict[str, Any] | None = None,
    artifact_json: dict[str, Any] | None = None,
) -> str:
    """Render a single ``{{Translation | …}}`` template invocation.

    Returns the bare template call (no surrounding comment, no
    trailing newline) — callers append it to a parent entity's page
    after the entity's structural row. Either SID may be ``None``;
    if both are missing, returns ``""`` (skip — caller filters).
    ``unit_json`` / ``ability_json`` are forwarded to the resolver
    for placeholder substitution context (used by unit and
    unit-ability translations); pass ``None`` for everything else.
    See D-026.
    """
    if not name_sid and not desc_sid:
        return ""

    params: dict[str, Any] = {
        "type": translation_type,
        "target_id": target_id,
        "name_sid": name_sid,
        "desc_sid": desc_sid,
    }
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        if name_sid:
            params[f"{code}_name"] = _lookup_text(
                name_sid, lang_dir, corpus, resolver, unit_json, ability_json,
                spec_json=spec_json, magic_json=magic_json, set_json=set_json,
                artifact_json=artifact_json,
            )
        if desc_sid:
            params[f"{code}_desc"] = _lookup_text(
                desc_sid, lang_dir, corpus, resolver, unit_json, ability_json,
                spec_json=spec_json, magic_json=magic_json, set_json=set_json,
                artifact_json=artifact_json,
            )

    return render_call("Translation", params, key_order=_TRANSLATION_FIELD_ORDER)


def iter_entry_seeds() -> Iterator[tuple[str, str]]:
    """Yield (type, subtype) pairs in canonical declaration order."""
    for entry_type, subtypes in ENTRY_SEEDS.items():
        for subtype in subtypes:
            yield (entry_type, subtype)


def render_entry_block(
    entry_type: str,
    subtype: str,
    name_sid: str,
    desc_sid: str | None,
    corpus: LocalizationCorpus,
    *,
    display_name_fallback: str | None = None,
    icon: str | None = None,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render a single ``{{Entry | …}}`` template invocation.

    Returns just the bare template call (no surrounding comment, no
    trailing newline). Use ``emit_entry_page`` when you want a complete
    standalone wiki page; use this when you're embedding the row in
    another emitter's output (e.g. faction pages embedding their city
    rows). See D-024.
    """
    en_name = _lookup_text(name_sid, "english", corpus, resolver, None, None)
    en_desc = (
        _lookup_text(desc_sid, "english", corpus, resolver, None, None)
        if desc_sid else None
    )

    params: dict[str, Any] = {
        "type": entry_type,
        "subtype": subtype,
        "display_name": en_name or display_name_fallback,
        "description": en_desc,
        "icon": icon,
        "name_sid": name_sid,
        "desc_sid": desc_sid,
    }
    for lang_dir in _TRANSLATION_LANG_ORDER:
        code = LANG_CODE[lang_dir]
        params[f"{code}_name"] = _lookup_text(
            name_sid, lang_dir, corpus, resolver, None, None
        )
        if desc_sid:
            params[f"{code}_desc"] = _lookup_text(
                desc_sid, lang_dir, corpus, resolver, None, None
            )

    return render_call("Entry", params, key_order=_ENTRY_FIELD_ORDER)


def emit_entry_page(
    entry_type: str,
    subtype: str,
    name_sid: str,
    desc_sid: str | None,
    corpus: LocalizationCorpus,
    *,
    display_name_fallback: str | None = None,
    icon: str | None = None,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render a complete ``Data:<EntryType>/<subtype>`` page — the
    bot-managed comment header plus one ``{{Entry | …}}`` call.

    Callers pass the SIDs directly so this serves both hand-curated
    seeds (via ``emit_entry_page_from_seed``) and per-patch extracted
    Entry data. ``desc_sid`` may be ``None`` for entries that have
    only a name — description columns are then sparse-emitted.
    """
    block = render_entry_block(
        entry_type=entry_type,
        subtype=subtype,
        name_sid=name_sid,
        desc_sid=desc_sid,
        corpus=corpus,
        display_name_fallback=display_name_fallback,
        icon=icon,
        resolver=resolver,
    )
    return (
        "<!-- Bot-managed page. Edit the source in artificer-bot, not here. -->\n\n"
        + block
        + "\n"
    )


def emit_entry_page_from_seed(
    entry_type: str,
    subtype: str,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Convenience wrapper: render a curated ``ENTRY_SEEDS`` entry."""
    seed = ENTRY_SEEDS[entry_type][subtype]
    return emit_entry_page(
        entry_type=entry_type,
        subtype=subtype,
        name_sid=seed["name_sid"],
        desc_sid=seed["desc_sid"],
        corpus=corpus,
        resolver=resolver,
        display_name_fallback=seed.get("display_name_fallback"),
        icon=seed.get("icon"),
    )


# ----------------------------------------------------------------------------
# Shared AttackPassive seed-data emitter
# ----------------------------------------------------------------------------

_ATTACK_PASSIVE_FIELD_ORDER: tuple[str, ...] = (
    "attack_passive_id", "pattern_token", "rank",
    "name_sid", "desc_sid", "display_name", "description",
)

def emit_attack_passive_page(
    attack_passive_id: str,
    info: dict[str, Any],
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:AttackPassive/<attack_passive_id>`` — one
    ``{{AttackPassive | …}}`` call (English defaults) plus one
    ``{{Translation | type=attack_passive | …}}`` row (per D-026).
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

    blocks = [
        "<!-- Bot-managed page. Edit the source in artificer-bot, not here. -->",
        render_call(
            "AttackPassive",
            parent_params,
            key_order=_ATTACK_PASSIVE_FIELD_ORDER,
        ),
    ]
    xlat = render_translation_block(
        translation_type="attack_passive",
        target_id=attack_passive_id,
        name_sid=name_sid if isinstance(name_sid, str) else None,
        desc_sid=desc_sid if isinstance(desc_sid, str) else None,
        corpus=corpus,
        resolver=resolver,
    )
    if xlat:
        blocks.append(xlat)
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

    unit_xlat = _render_unit_translation(unit, corpus, resolver, unit_json)
    if unit_xlat:
        blocks.append(unit_xlat)
    for ability in unit.unit_abilities:
        ab_xlat = _render_ability_translation(unit.id, ability, corpus, resolver, unit_json)
        if ab_xlat:
            blocks.append(ab_xlat)

    return "\n\n".join(blocks) + "\n"


def _lookup_text(
    sid: str | None, lang: str, corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None, unit_json: dict[str, Any] | None,
    ability_json: dict[str, Any] | None = None,
    spec_json: dict[str, Any] | None = None,
    magic_json: dict[str, Any] | None = None,
    set_json: dict[str, Any] | None = None,
    artifact_json: dict[str, Any] | None = None,
) -> str | None:
    if not sid:
        return None
    raw = corpus.get(sid, lang)
    if raw is None:
        return None
    if resolver is not None:
        return resolver.resolve(
            sid, raw, unit_json,
            lang=lang, ability_json=ability_json, spec_json=spec_json,
            magic_json=magic_json, set_json=set_json, artifact_json=artifact_json,
        )
    return html_to_wiki(raw)


def _ability_json_for(ability: UnitAbility, unit_json: dict[str, Any] | None) -> dict[str, Any] | None:
    if unit_json is None:
        return None
    # Preferred path: use the source-array provenance recorded at extract
    # time. This handles the case where alternativeAttacks consume some
    # ordinals before the regular abilities[] list — the `ordinal` then
    # doesn't match the JSON index (e.g. black_dragon Inner Flame is
    # ordinal=2 but lives at logic.abilities[0]).
    if ability.source_array and ability.source_index is not None:
        arr = unit_json.get(ability.source_array)
        if isinstance(arr, list) and 0 <= ability.source_index < len(arr):
            entry = arr[ability.source_index]
            return entry if isinstance(entry, dict) else None
        return None
    # Fallback: derive from ordinal alone (correct for ability_types
    # whose ordinals trivially match the JSON array, currently
    # passive / conditional_passive / global_passive / aura).
    if ability.ordinal is None:
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
    """Per D-026: emit unified ``{{Translation | type=unit | …}}``."""
    return render_translation_block(
        translation_type="unit",
        target_id=unit.id,
        name_sid=unit.name_sid,
        desc_sid=unit.narrative_description_sid,
        corpus=corpus,
        resolver=resolver,
        unit_json=unit_json,
    )


def _render_ability_translation(
    unit_id: str, ability: UnitAbility, corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None, unit_json: dict[str, Any] | None = None,
) -> str:
    """Per D-026: emit unified ``{{Translation | type=unit_ability | …}}``.

    The composite ability_id stays the join key. Filter columns
    (unit_id, ability_type, ordinal, variant) previously inlined here
    are dropped — display layer joins ``UnitAbility`` for those when
    needed. Returns ``""`` if the ability has neither name nor desc
    SIDs to translate; the caller filters empties before joining.
    """
    return render_translation_block(
        translation_type="unit_ability",
        target_id=make_ability_id(unit_id, ability.ability_type, ability.ordinal, ability.variant),
        name_sid=ability.name_sid,
        desc_sid=ability.desc_sid,
        corpus=corpus,
        resolver=resolver,
        unit_json=unit_json,
        ability_json=_ability_json_for(ability, unit_json),
    )


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
