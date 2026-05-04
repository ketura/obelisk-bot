"""Extract :class:`Unit` records from a patch dump.

This pass:

* Stores attack and ``raw_*`` passive/ability/aura blocks verbatim.
* Pulls ``creature_type`` / ``immunities`` / ``disablers`` from the
  ``data_immunities`` and ``data_disablers``-shaped passives. Creature-class
  immunity tags (``living_immunities``, ``undead_immunities``, etc.) feed
  ``creature_type``; everything else feeds ``immunities``.
* Logs but doesn't fail on unknown fields.

The consolidated :attr:`Unit.unit_abilities` list is populated post-extract
in :func:`extract_units_enriched` via the pattern-detector pipeline in
:mod:`artificer.match`.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from artificer.extract.loader import CorePaths, iter_array, load_json
from artificer.extract._pattern_passive_map import lookup_attack_passive
from artificer.models.common import Faction, ResourceCost
from artificer.models.unit import AttackSlot, Unit, UnitAbility, UnitAttack, UnitStats

logger = logging.getLogger(__name__)


_DIR_TO_FACTION: dict[str, Faction] = {
    "humans": Faction.HUMAN,
    "undead": Faction.UNDEAD,
    "dungeon": Faction.DUNGEON,
    "nature": Faction.NATURE,
    "demons": Faction.DEMON,
    "unfrozen": Faction.UNFROZEN,
    "neutral": Faction.NEUTRAL,
}

_FRACTION_FIELD_MAP: dict[str, Faction] = {
    "human": Faction.HUMAN,
    "undead": Faction.UNDEAD,
    "dungeon": Faction.DUNGEON,
    "nature": Faction.NATURE,
    "demon": Faction.DEMON,
    "unfrozen": Faction.UNFROZEN,
    "neutral": Faction.NEUTRAL,
}


_CREATURE_CLASS_TAGS: frozenset[str] = frozenset(
    {
        "living_immunities",
        "undead_immunities",
        "demon_immunities",
        "magic_creature_immunities",
        "embodiment_immunities",
        "dragon_immunities",
        "construct_immunities",
    }
)


@dataclass
class UnitExtractionResult:
    """Outcome of a unit extraction run."""

    units: list[Unit] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    warnings: list[tuple[Path, str]] = field(default_factory=list)
    audit_report: Any = None  # AuditReport, late-imported

    @property
    def by_id(self) -> dict[str, Unit]:
        return {u.id: u for u in self.units}


def extract_units(paths: CorePaths) -> UnitExtractionResult:
    """Walk every ``Core/DB/units/units_logics/**/*_l.json`` and extract one
    :class:`Unit` per array entry. Does not populate ``unit_abilities``."""
    result = UnitExtractionResult()
    root = paths.units_logics_dir()
    if not root.is_dir():
        raise FileNotFoundError(f"units_logics dir not found: {root}")

    for jp in sorted(root.rglob("*_l.json")):
        if not jp.is_file():
            continue
        try:
            faction_dir = jp.parent.name
            fallback = _DIR_TO_FACTION.get(faction_dir, Faction.NEUTRAL)
            doc = load_json(jp)
            for raw in iter_array(doc):
                unit = _build_unit(
                    raw=raw,
                    source_path=jp.relative_to(paths.core_root).as_posix(),
                    fallback_faction=fallback,
                    warnings=result.warnings,
                    file_path=jp,
                )
                if unit is not None:
                    result.units.append(unit)
        except Exception as exc:  # noqa: BLE001
            result.skipped.append((jp, f"{type(exc).__name__}: {exc}"))
            logger.warning("Failed to extract %s: %s", jp, exc)

    return result


def extract_units_enriched(paths: CorePaths) -> UnitExtractionResult:
    """Extract units, then read views files to populate ``unit_abilities``.

    The views file (``Core/DB/units/units_views/<faction>/<id>_v.json``) is
    the authoritative SID list per unit. Each entry has explicit ``name``
    and ``description`` SIDs. We classify each SID by prefix:

    * ``base_*``                  → DROP (looked up via unit attributes)
    * ``<faction>_*`` for unit's faction → DROP (looked up via Faction enum)
    * everything else             → KEEP — emit a UnitAbility row

    The dropped categories are not duplicated on each unit's page; the wiki
    display layer recovers them from the unit's stored attributes
    (creature_type, faction, attack penetration, move type, etc.).

    Audit reports JSON-shape patterns the views file omits, plus any unit-
    specific SID that's referenced but missing from the L10n corpus.
    """
    from artificer.extract.localization import load_localization_corpus
    from artificer.extract.views import load_views
    from artificer.match import AuditReport, audit_unit

    base = extract_units(paths)
    unit_index: dict[str, Unit] = {u.id: u for u in base.units}
    views = load_views(paths)

    # Load just english localization for the "unused" detection: units whose
    # name SID has no english entry are deprecated content the game ships
    # but doesn't expose. Cheap to load (single language).
    name_corpus = load_localization_corpus(paths, languages={"english"})

    # Faction prefixes for drop classification — name SIDs starting with one
    # of these (followed by ``_``) are faction-shared.
    faction_prefixes = {f.value for f in Faction}

    def is_base_sid(sid: str) -> bool:
        # ``base_*`` (cross-cutting passives) and ``common_*`` (shared
        # alt-attack names like "Melee Attack" / "Single Shot") both
        # route to shared_abilities.
        return sid.startswith("base_") or sid.startswith("common_")

    def is_faction_sid(sid: str, unit_faction: str) -> bool:
        return any(sid.startswith(f + "_") for f in faction_prefixes)

    audit = AuditReport()
    enriched: list[Unit] = []
    for u in base.units:
        view = views.get(u.id, {}) or {}
        abilities: list[UnitAbility] = []
        seen_slots: set[tuple[str, int | None]] = set()
        shared: list[str] = []  # base_* / <faction>_* name SIDs, in views order
        seen_shared: set[str] = set()

        # Walk views in order: alternativeAttacks (Fighting Styles like
        # Sulfurous Assault, Arrow Barrage), then abilities (regular
        # active abilities), both as ``active`` ability_type. The
        # shared ordinal counter aligns with the SID numbering — e.g.
        # medusa_ability_1 (Arrow Barrage in alt[1]) gets ordinal 1,
        # medusa_ability_2 (Stone Gaze in abilities[0]) gets ordinal 2.
        active_ordinal = 0
        for source_key, raw_array in (
            ("alternativeAttacks", u.alternative_attacks),
            ("abilities", u.raw_abilities),
        ):
            for source_idx, entry in enumerate(view.get(source_key, []) or []):
                if not isinstance(entry, dict):
                    continue
                name_sid = entry.get("name")
                desc_sid = entry.get("description")
                if not isinstance(name_sid, str) or not name_sid:
                    continue
                # base_*, common_*, faction_* route to shared_abilities.
                if is_base_sid(name_sid) or is_faction_sid(name_sid, u.faction.value):
                    if name_sid not in seen_shared:
                        seen_shared.add(name_sid)
                        shared.append(name_sid)
                    continue
                active_ordinal += 1
                slot_key = ("active", active_ordinal)
                if slot_key in seen_slots:
                    continue
                seen_slots.add(slot_key)

                # JSON enrichment: index by source array position, not
                # ordinal (they diverge when shared entries are skipped).
                extra_fields: dict[str, Any] = {}
                if 0 <= source_idx < len(raw_array):
                    extra_fields = _active_fields_from_json(raw_array[source_idx])

                abilities.append(
                    UnitAbility(
                        ability_type="active",
                        ordinal=active_ordinal,
                        variant=None,
                        name_sid=name_sid,
                        desc_sid=desc_sid if isinstance(desc_sid, str) else None,
                        **extra_fields,
                    )
                )

        # Now the passives.
        passive_ordinal = 0
        for entry in view.get("passives", []) or []:
            if not isinstance(entry, dict):
                continue
            name_sid = entry.get("name")
            desc_sid = entry.get("description")
            if not isinstance(name_sid, str) or not name_sid:
                continue
            if is_base_sid(name_sid) or is_faction_sid(name_sid, u.faction.value):
                if name_sid not in seen_shared:
                    seen_shared.add(name_sid)
                    shared.append(name_sid)
                continue
            passive_ordinal += 1
            slot_key = ("passive", passive_ordinal)
            if slot_key in seen_slots:
                continue
            seen_slots.add(slot_key)
            abilities.append(
                UnitAbility(
                    ability_type="passive",
                    ordinal=passive_ordinal,
                    variant=None,
                    name_sid=name_sid,
                    desc_sid=desc_sid if isinstance(desc_sid, str) else None,
                )
            )

        # Synthesize rows for ability types that don't appear in views:
        # aura (singular), conditional_passive[N], global_passive[N].
        # Their name_sid is synthetic — these entries don't have user-
        # facing icons in the same way; the wiki template displays them
        # via their tag/condition fields.
        if u.aura:
            abilities.append(
                UnitAbility(
                    ability_type="aura",
                    ordinal=1,
                    variant=None,
                    name_sid=f"{u.id}_aura_1_name",
                    **_aura_fields_from_json(u.aura),
                )
            )
        for i, gp in enumerate(u.raw_global_passives, start=1):
            abilities.append(
                UnitAbility(
                    ability_type="global_passive",
                    ordinal=i,
                    variant=None,
                    name_sid=f"{u.id}_global_passive_{i}_name",
                    **_global_passive_fields_from_json(gp),
                )
            )
        for i, cp in enumerate(u.raw_conditional_passives, start=1):
            abilities.append(
                UnitAbility(
                    ability_type="conditional_passive",
                    ordinal=i,
                    variant=None,
                    name_sid=f"{u.id}_conditional_passive_{i}_name",
                    **_conditional_fields_from_json(cp),
                )
            )

        # D-021 (revised): one UnitAttack record per unit, with default/
        # counter/alt/alt2 slots. Pattern-passives ride on the slots'
        # passive_id field; they're no longer synthesized as UnitAbility rows.
        unit_attack_record, todo_patterns = build_unit_attack(u)
        for tp in todo_patterns:
            logger.warning(
                "Unmapped attack pattern_sid %r on unit %s — slot's passive_id set to TODO placeholder",
                tp,
                u.id,
            )

        abilities.sort(
            key=lambda a: (a.ability_type, -1 if a.ordinal is None else a.ordinal, a.name_sid)
        )

        # Detect deprecated/unused units: no english localization for the
        # primary name SID.
        unused = name_corpus.get(u.name_sid, "english") is None

        enriched.append(
            u.model_copy(
                update={
                    "unit_abilities": tuple(abilities),
                    "unit_attack": unit_attack_record,
                    "shared_abilities": tuple(shared),
                    "unused": unused,
                }
            )
        )

        # Audit: compare logic JSON against views, surface gaps (D-017).
        audit.units.append(
            audit_unit(
                unit=u,
                views_entry=view if view else None,
                family_root=_family_root_of(u, unit_index),
            )
        )

    return UnitExtractionResult(
        units=enriched,
        skipped=base.skipped,
        warnings=base.warnings,
        audit_report=audit,
    )


def _family_root_of(u: Unit, unit_index: dict[str, Unit]) -> str:
    cur = u
    while cur.base_sid and cur.base_sid in unit_index:
        cur = unit_index[cur.base_sid]
    return cur.id


# ---------------------------------------------------------------------------


def _build_unit(
    *,
    raw: dict[str, Any],
    source_path: str,
    fallback_faction: Faction,
    warnings: list[tuple[Path, str]],
    file_path: Path,
) -> Unit | None:
    unit_id = raw.get("id")
    if not isinstance(unit_id, str):
        warnings.append((file_path, "skipping entry with missing/non-string 'id'"))
        return None

    fraction = raw.get("fraction")
    faction = (
        _FRACTION_FIELD_MAP.get(fraction, fallback_faction)
        if isinstance(fraction, str)
        else fallback_faction
    )

    raw_passives = _dict_tuple(raw.get("passives"))
    raw_conditional_passives = _dict_tuple(raw.get("conditionalPassives"))
    raw_global_passives = _dict_tuple(raw.get("globalPassives"))
    raw_abilities = _dict_tuple(raw.get("abilities"))

    creature_type, immunities, disablers = _classify_passive_attributes(
        raw_passives + raw_conditional_passives + raw_global_passives
    )

    return Unit(
        id=unit_id,
        faction=faction,
        tier=int(raw.get("tier", 0)),
        source_path=source_path,
        name_sid=str(raw.get("nameSid") or f"{unit_id}_name"),
        narrative_description_sid=f"{unit_id}_narrativeDescription",
        base_sid=_str_or_none(raw.get("baseSid")),
        upgrade_sid=_str_or_none(raw.get("upgradeSid")),
        stats=_build_stats(raw.get("stats"), warnings, file_path),
        raw_stats=raw.get("stats") if isinstance(raw.get("stats"), dict) else {},
        cost=tuple(_iter_costs(raw.get("unitCost"))),
        default_attacks=_dict_tuple(raw.get("defaultAttacks")),
        counter_attacks=_dict_tuple(raw.get("counterAttacks")),
        alternative_attacks=_dict_tuple(raw.get("alternativeAttacks")),
        raw_passives=raw_passives,
        raw_conditional_passives=raw_conditional_passives,
        raw_global_passives=raw_global_passives,
        raw_abilities=raw_abilities,
        aura=raw.get("aura") if isinstance(raw.get("aura"), dict) else None,
        creature_type=creature_type,
        immunities=immunities,
        disablers=disablers,
        native_biome=_str_or_none(raw.get("nativeBiome")),
        ai_archetype=_str_or_none(raw.get("ai")),
        tags=tuple(t for t in (raw.get("tags") or ()) if isinstance(t, str)),
        leave_corpse=raw.get("leaveCorpse") if isinstance(raw.get("leaveCorpse"), bool) else None,
        squad_value=_int_or_none(raw.get("squadValue")),
        exp_bonus=_int_or_none(raw.get("expBonus")),
    )


def _classify_passive_attributes(
    passive_blocks: tuple[dict[str, Any], ...],
) -> tuple[str | None, tuple[str, ...], tuple[str, ...]]:
    creature_type: str | None = None
    immunities: list[str] = []
    disablers: list[str] = []

    for block in passive_blocks:
        if not isinstance(block, dict):
            continue
        data = block.get("data") if isinstance(block.get("data"), dict) else None
        if data is None:
            continue
        for entry in data.get("immunities", []) or []:
            if not isinstance(entry, dict):
                continue
            for tag in entry.get("tags", []) or ():
                if not isinstance(tag, str):
                    continue
                if tag in _CREATURE_CLASS_TAGS:
                    if creature_type is None:
                        creature_type = tag.removesuffix("_immunities")
                else:
                    immunities.append(tag)
        for entry in data.get("disablers", []) or []:
            if not isinstance(entry, dict):
                continue
            mech = entry.get("mech")
            if isinstance(mech, str):
                disablers.append(mech)

    return creature_type, tuple(dict.fromkeys(immunities)), tuple(dict.fromkeys(disablers))


def _build_stats(
    raw: Any,
    warnings: list[tuple[Path, str]],
    file_path: Path,
) -> UnitStats:
    if not isinstance(raw, dict):
        warnings.append((file_path, "stats block missing or not a dict; using zeros"))
        raw = {}
    return UnitStats(
        hp=int(raw.get("hp", 0)),
        offence=int(raw.get("offence", 0)),
        defence=int(raw.get("defence", 0)),
        damage_min=int(raw.get("damageMin", 0)),
        damage_max=int(raw.get("damageMax", 0)),
        initiative=int(raw.get("initiative", 0)),
        speed=int(raw.get("speed", 0)),
        luck=int(raw.get("luck", 0)),
        morale=int(raw.get("moral", 0)),
        energy_per_cast=int(raw.get("energyPerCast", 0)),
        energy_per_round=int(raw.get("energyPerRound", 0)),
        energy_per_take_damage=int(raw.get("energyPerTakeDamage", 0)),
        action_points=int(raw.get("actionPoints", 1)),
        num_counters=int(raw.get("numCounters", 1)),
        morale_min=int(raw.get("moralMin", -3)),
        morale_max=int(raw.get("moralMax", 3)),
        luck_min=int(raw.get("luckMin", -3)),
        luck_max=int(raw.get("luckMax", 3)),
        move_type=str(raw.get("moveType", "ground")),
        in_damage_mods=_damage_mod_tuple(raw.get("inDmgMods")),
        out_damage_mods=_damage_mod_tuple(raw.get("outDmgMods")),
    )


def _damage_mod_tuple(block: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(block, dict):
        return ()
    items = block.get("list", [])
    if not isinstance(items, list):
        return ()
    return tuple(item for item in items if isinstance(item, dict))


def _iter_costs(raw: Any) -> Iterable[ResourceCost]:
    if not isinstance(raw, dict):
        return
    arr = raw.get("costResArray", [])
    if not isinstance(arr, list):
        return
    for entry in arr:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        amount = entry.get("cost")
        if isinstance(name, str) and isinstance(amount, int):
            yield ResourceCost(resource=name, amount=amount)


def _dict_tuple(v: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(v, list):
        return ()
    return tuple(item for item in v if isinstance(item, dict))


def _str_or_none(v: Any) -> str | None:
    return v if isinstance(v, str) and v else None


def _int_or_none(v: Any) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    return None


# ----------------------------------------------------------------------------
# JSON -> UnitAbility splinter-table field extractors (D-019)
# ----------------------------------------------------------------------------


# (game-key, model-attr) — applied verbatim as field copies.
_ACTIVE_TOPLEVEL_MAP: tuple[tuple[str, str], ...] = (
    ("attackType_", "attack_type"),
    ("rank", "rank"),
    ("cd", "cd"),
    ("energyLevel", "energy_level"),
    ("actionCost", "action_cost"),
    ("charges", "charges"),
    ("disableForAi", "disable_for_ai"),
    ("neverDisable", "never_disable"),
    ("moveType", "move_type_active"),
    ("useAllEnergyLevels", "use_all_energy_levels"),
    ("dontUseEnergy", "dont_use_energy"),
    ("untargetedCast", "untargeted_cast"),
)

_DEALER_FIELD_MAP: tuple[tuple[str, str], ...] = (
    ("attackPatternSid", "attack_pattern_sid"),
    ("damageTarget_", "damage_target"),
    ("damageType_", "damage_type"),
    ("statDmgMult", "stat_dmg_mult"),
    ("triggerCounter", "trigger_counter"),
    ("multitargetType", "multitarget_type"),
    ("numTargets", "num_targets"),
    ("instacast", "instacast"),
    ("dontTriggerEnergyRegen", "dont_trigger_energy_regen"),
    ("returnToStartAfterAttack", "return_to_start_after_attack"),
    ("untargetedCast", "untargeted_cast"),  # also seen on dealer
    ("minBaseDmg", "min_base_dmg"),
    ("maxBaseDmg", "max_base_dmg"),
    ("minStackDmg", "min_stack_dmg"),
    ("maxStackDmg", "max_stack_dmg"),
    ("minDamagePerEnergyLevel", "min_damage_per_energy_level"),
    ("maxDamagePerEnergyLevel", "max_damage_per_energy_level"),
    ("damageMultiplerPerHeroLevel", "damage_multipler_per_hero_level"),
    ("tempSelfBuff", "temp_self_buff"),
    ("shootRange", "shoot_range"),
    ("shootThreshold", "shoot_threshold"),
    ("shootRedCount", "shoot_red_count"),
    ("shootDmgBuff", "shoot_dmg_buff"),
    ("useSpeedAsShootRange", "use_speed_as_shoot_range"),
    ("buffTarget_", "buff_target"),
)


def _active_fields_from_json(ab_json: dict[str, Any]) -> dict[str, Any]:
    """Pull active-ability scalars from a unit's ``abilities[N]`` JSON entry.

    Reads top-level fields, then drills into ``damageDealer`` for the
    bulk of the dealer/buff/shoot/target params. Only sets keys that
    were present in the source — nothing is fabricated, so the
    UnitAbility model's defaults govern unset fields.
    """
    out: dict[str, Any] = {}
    if not isinstance(ab_json, dict):
        return out

    for src, dst in _ACTIVE_TOPLEVEL_MAP:
        if src in ab_json:
            out[dst] = ab_json[src]

    dd = ab_json.get("damageDealer")
    if not isinstance(dd, dict):
        return out

    for src, dst in _DEALER_FIELD_MAP:
        if src in dd:
            out[dst] = dd[src]

    # buff sub-dict
    buff = dd.get("buff")
    if isinstance(buff, dict):
        if "sid" in buff:
            out["buff_sid"] = buff["sid"]
        if "duration" in buff:
            out["buff_duration"] = buff["duration"]
        if "charges" in buff:
            out["buff_charges"] = buff["charges"]

    # cast/affect target params
    for prefix, src_key in (("cast", "castTargetParams"), ("affect", "affectTargetParams")):
        params = dd.get(src_key)
        if not isinstance(params, dict):
            continue
        if "castTarget_" in params:
            out[f"{prefix}_target"] = params["castTarget_"]
        if "selection" in params:
            out[f"{prefix}_selection"] = params["selection"]
        if "targetCondition_" in params:
            out[f"{prefix}_target_condition"] = params["targetCondition_"]
        tags = params.get("targetTags")
        if isinstance(tags, list):
            out[f"{prefix}_target_tags"] = tuple(t for t in tags if isinstance(t, str))

    return out


def _conditional_fields_from_json(p_json: dict[str, Any]) -> dict[str, Any]:
    """Pull condition + stats from a conditionalPassives[N] entry."""
    out: dict[str, Any] = {}
    cond = p_json.get("condition")
    if isinstance(cond, list):
        if len(cond) >= 1 and isinstance(cond[0], str):
            out["condition_check"] = cond[0]
        if len(cond) >= 2 and isinstance(cond[1], str):
            out["condition_target"] = cond[1]
        if len(cond) >= 3 and isinstance(cond[2], str):
            out["condition_value"] = cond[2]
    stats = p_json.get("stats")
    if isinstance(stats, dict) and stats:
        k, v = next(iter(stats.items()))
        if isinstance(k, str):
            out["affected_stat"] = k
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out["affected_stat_amount"] = float(v)
    return out


def _global_passive_fields_from_json(p_json: dict[str, Any]) -> dict[str, Any]:
    """Pull globalPassives[N] scalars."""
    out: dict[str, Any] = {}
    if isinstance(p_json.get("target"), str):
        out["global_target"] = p_json["target"]
    power = p_json.get("power")
    if isinstance(power, int) and not isinstance(power, bool):
        out["global_power"] = power
    if isinstance(p_json.get("tag"), str):
        out["global_tag"] = p_json["tag"]
    data = p_json.get("data")
    if isinstance(data, dict):
        stats = data.get("stats")
        if isinstance(stats, dict) and stats:
            k, v = next(iter(stats.items()))
            if isinstance(k, str):
                out["affected_stat"] = k
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out["affected_stat_amount"] = float(v)
    return out


def _aura_fields_from_json(a_json: dict[str, Any]) -> dict[str, Any]:
    """Pull aura scalars."""
    out: dict[str, Any] = {}
    if isinstance(a_json.get("target"), str):
        out["aura_target"] = a_json["target"]
    power = a_json.get("power")
    if isinstance(power, int) and not isinstance(power, bool):
        out["aura_power"] = power
    radius = a_json.get("radius")
    if isinstance(radius, int) and not isinstance(radius, bool):
        out["aura_radius"] = radius
    if isinstance(a_json.get("tag"), str):
        out["aura_tag"] = a_json["tag"]
    data = a_json.get("data")
    if isinstance(data, dict):
        stats = data.get("stats")
        if isinstance(stats, dict) and stats:
            k, v = next(iter(stats.items()))
            if isinstance(k, str):
                out["affected_stat"] = k
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out["affected_stat_amount"] = float(v)
    return out



# ----------------------------------------------------------------------------
# JSON -> UnitAttack record (D-021, revised: one row per unit)
# ----------------------------------------------------------------------------


# JSON `attackType_` -> Cargo `attack_type` enum (player-facing rename).
_ATTACK_TYPE_FROM_JSON: dict[str, str] = {
    "melee": "melee",
    "shoot": "ranged",
    "range": "reach",
}

# Top-level fields on an attack entry copied through (when present).
_ATTACK_TOPLEVEL_MAP: tuple[tuple[str, str], ...] = (
    ("cd", "cd"),
    ("dontUseEnergy", "dont_use_energy"),
    ("returnToStartAfterAttack", "return_to_start_after_attack"),
    ("neverDisable", "never_disable"),
)

# damageDealer fields copied through.
_ATTACK_DEALER_MAP: tuple[tuple[str, str], ...] = (
    ("damageTarget_", "damage_target"),
    ("damageType_", "damage_type"),
    ("statDmgMult", "stat_dmg_mult"),
    ("triggerCounter", "trigger_counter"),
    ("multitargetType", "multitarget_type"),
    ("numTargets", "num_targets"),
    ("dontTriggerEnergyRegen", "dont_trigger_energy_regen"),
    ("returnToStartAfterAttack", "return_to_start_after_attack"),
    ("tempSelfBuff", "temp_self_buff"),
)


def _build_attack_slot(
    *, raw: dict[str, Any], unit_id: str
) -> tuple[AttackSlot | None, str | None]:
    """Build one AttackSlot from a raw JSON attack entry.

    Returns ``(slot, todo_pattern_sid)``. ``slot`` is None if the entry
    lacks a recognizable ``attackType_``. ``todo_pattern_sid`` is the
    raw pattern_sid if its passive_id resolution fell through to a TODO
    placeholder (caller logs); otherwise None.
    """
    if not isinstance(raw, dict):
        return (None, None)
    json_attack_type = raw.get("attackType_")
    if not isinstance(json_attack_type, str):
        return (None, None)
    cargo_attack_type = _ATTACK_TYPE_FROM_JSON.get(json_attack_type)
    if cargo_attack_type is None:
        return (None, None)

    fields: dict[str, Any] = {"attack_type": cargo_attack_type}

    for src, dst in _ATTACK_TOPLEVEL_MAP:
        if src in raw:
            fields[dst] = raw[src]

    dd = raw.get("damageDealer")
    pattern_sid: str | None = None
    if isinstance(dd, dict):
        for src, dst in _ATTACK_DEALER_MAP:
            if src in dd:
                fields[dst] = dd[src]

        pattern = dd.get("attackPatternSid")
        if isinstance(pattern, str):
            pattern_sid = pattern
            fields["pattern_sid"] = pattern

        # affect_target lives in affectTargetParams.castTarget_
        affect_params = dd.get("affectTargetParams")
        if isinstance(affect_params, dict):
            ct = affect_params.get("castTarget_")
            if isinstance(ct, str):
                fields["affect_target"] = ct

        # buff slot
        buff = dd.get("buff")
        if isinstance(buff, dict):
            sid = buff.get("sid")
            duration = buff.get("duration")
            if isinstance(sid, str):
                fields["buff_sid"] = sid
            if isinstance(duration, int) and not isinstance(duration, bool):
                fields["buff_duration"] = duration
        if isinstance(dd.get("buffTarget_"), str):
            fields["buff_target"] = dd["buffTarget_"]

        # is_armed_ability — derived from tag presence
        tags = dd.get("tags") or []
        if any(
            isinstance(t, str) and t.startswith("armed_ability") for t in tags
        ):
            fields["is_armed_ability"] = True

    # Resolve passive_id from pattern_sid via the curated map.
    todo_pattern: str | None = None
    if pattern_sid is not None:
        passive_id, is_todo = lookup_attack_passive(
            pattern_sid=pattern_sid, unit_id=unit_id
        )
        if passive_id is not None:
            fields["passive_id"] = passive_id
            if is_todo:
                fields["passive_id_is_todo"] = True
                todo_pattern = pattern_sid

    return (AttackSlot(**fields), todo_pattern)


def build_unit_attack(u: Unit) -> tuple[UnitAttack | None, list[str]]:
    """Walk a Unit's default/counter/alternative attack arrays and produce
    a single :class:`UnitAttack` record with the four optional slots.

    Returns ``(unit_attack, todo_patterns)``. The list contains every
    pattern_sid that fell through to a TODO placeholder so the caller
    can log warnings.
    """
    todos: list[str] = []

    def first_slot(raw_seq: tuple[dict[str, Any], ...]) -> AttackSlot | None:
        for raw in raw_seq:
            slot, todo = _build_attack_slot(raw=raw, unit_id=u.id)
            if slot is not None:
                if todo is not None:
                    todos.append(todo)
                return slot
        return None

    default_slot = first_slot(u.default_attacks)
    counter_slot = first_slot(u.counter_attacks)

    # Alternative attacks: take up to two. The first becomes ``alt``,
    # second becomes ``alt2``. Skip any that fail to parse.
    alt_slot: AttackSlot | None = None
    alt2_slot: AttackSlot | None = None
    parsed_alts: list[AttackSlot] = []
    for raw in u.alternative_attacks:
        slot, todo = _build_attack_slot(raw=raw, unit_id=u.id)
        if slot is not None:
            if todo is not None:
                todos.append(todo)
            parsed_alts.append(slot)
    if len(parsed_alts) >= 1:
        alt_slot = parsed_alts[0]
    if len(parsed_alts) >= 2:
        alt2_slot = parsed_alts[1]

    if all(s is None for s in (default_slot, counter_slot, alt_slot, alt2_slot)):
        return (None, todos)

    return (
        UnitAttack(
            unit_id=u.id,
            default=default_slot,
            counter=counter_slot,
            alt=alt_slot,
            alt2=alt2_slot,
        ),
        todos,
    )


# end-of-module sync sentinel
