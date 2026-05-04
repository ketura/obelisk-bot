"""Canonical Unit / UnitAbility / UnitAttack / AttackSlot models.

D-021 (revised): UnitAttack is one row per unit with four optional slots:
``default``, ``counter``, ``alt``, ``alt2``. Each slot is an
:class:`AttackSlot`. Pattern-passives (Sweeping/Whirlwind/Dragonbreath/
Cone/Area Strike) are referenced via ``passive_id`` against the shared
``AttackPassive`` Cargo table — *not* synthesized as UnitAbility rows.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from artificer.models.common import Faction, ResourceCost, Sid


class UnitStats(BaseModel):
    """A unit's combat stat block."""

    model_config = ConfigDict(frozen=True)

    hp: int
    offence: int
    defence: int
    damage_min: int
    damage_max: int

    initiative: int
    speed: int

    luck: int = 0
    morale: int = 0

    energy_per_cast: int = 0
    energy_per_round: int = 0
    energy_per_take_damage: int = 0

    action_points: int = 1
    num_counters: int = 1

    morale_min: int = -3
    morale_max: int = 3
    luck_min: int = -3
    luck_max: int = 3

    move_type: str = "ground"

    in_damage_mods: tuple[dict[str, Any], ...] = ()
    out_damage_mods: tuple[dict[str, Any], ...] = ()


class UnitAbility(BaseModel):
    """One row in the consolidated UnitAbility Cargo table."""

    model_config = ConfigDict(frozen=True)

    ability_type: str
    ordinal: int | None = None
    variant: str | None = None

    name_sid: Sid
    desc_sid: Sid | None = None

    affected_stat: str | None = None
    affected_stat_amount: float | None = None

    # Active-ability scalars
    attack_type: str | None = None
    rank: int | None = None
    cd: int | None = None
    energy_level: int | None = None
    action_cost: int | None = None
    charges: int | None = None
    disable_for_ai: bool | None = None
    never_disable: bool | None = None
    move_type_active: str | None = None
    use_all_energy_levels: bool | None = None
    dont_use_energy: bool | None = None
    untargeted_cast: bool | None = None
    instacast: bool | None = None

    # damageDealer core fields
    attack_pattern_sid: str | None = None
    damage_target: str | None = None
    damage_type: str | None = None
    stat_dmg_mult: float | None = None
    trigger_counter: bool | None = None
    multitarget_type: str | None = None
    num_targets: int | None = None
    dont_trigger_energy_regen: bool | None = None
    return_to_start_after_attack: bool | None = None

    # Direct damage tuning
    min_base_dmg: int | None = None
    max_base_dmg: int | None = None
    min_stack_dmg: int | None = None
    max_stack_dmg: int | None = None
    min_damage_per_energy_level: int | None = None
    max_damage_per_energy_level: int | None = None
    damage_multipler_per_hero_level: float | None = None
    temp_self_buff: str | None = None

    # Buff applied by the ability
    buff_sid: str | None = None
    buff_target: str | None = None
    buff_duration: int | None = None
    buff_charges: int | None = None

    # Ranged tuning
    shoot_range: int | None = None
    shoot_threshold: int | None = None
    shoot_red_count: int | None = None
    shoot_dmg_buff: float | None = None
    use_speed_as_shoot_range: bool | None = None

    # Cast/affect target params
    cast_target: str | None = None
    cast_selection: str | None = None
    cast_target_condition: str | None = None
    cast_target_tags: tuple[str, ...] = ()

    affect_target: str | None = None
    affect_selection: str | None = None
    affect_target_condition: str | None = None
    affect_target_tags: tuple[str, ...] = ()

    # Conditional passive
    condition_check: str | None = None
    condition_target: str | None = None
    condition_value: str | None = None

    # Global passive
    global_target: str | None = None
    global_power: int | None = None
    global_tag: str | None = None

    # Aura
    aura_target: str | None = None
    aura_power: int | None = None
    aura_radius: int | None = None
    aura_tag: str | None = None

    # Passive-only sequence effect
    sequence_effect: str | None = None


class AttackSlot(BaseModel):
    """One attack slot — default, counter, alt, or alt2.

    Sparse by design: most fields are None. The slot is "present" iff
    ``attack_type`` is set.
    """

    model_config = ConfigDict(frozen=True)

    attack_type: str
    """melee | ranged | reach (translated from JSON melee/shoot/range)"""

    pattern_sid: str | None = None
    """Engine-level pattern. Usually omitted on emit when canonical for
    the resolved ``passive_id``."""

    passive_id: str | None = None
    """FK to AttackPassive (e.g. 'sweeping_strike'). NULL when the
    attack pattern has no special passive (e.g. plain melee)."""

    passive_id_is_todo: bool = False
    """True if the bot synthesized a ``pattern_passive_TODO_*``
    placeholder (unmapped pattern). Used by the emitter to flag the
    row for human review and to suppress AttackPassive joins."""

    # Common dial overrides
    stat_dmg_mult: float | None = None
    damage_target: str | None = None
    affect_target: str | None = None
    trigger_counter: bool | None = None
    damage_type: str | None = None

    # On-hit buff slot
    buff_sid: str | None = None
    buff_target: str | None = None
    buff_duration: int | None = None

    # Top-level toggles
    cd: int | None = None
    dont_use_energy: bool | None = None
    return_to_start_after_attack: bool | None = None
    never_disable: bool | None = None

    # damageDealer scalars (rare)
    temp_self_buff: str | None = None
    dont_trigger_energy_regen: bool | None = None
    multitarget_type: str | None = None
    num_targets: int | None = None
    is_armed_ability: bool | None = None


class UnitAttack(BaseModel):
    """One row in the UnitAttack Cargo table — one per unit, four optional
    slots collapsed into a single wide row."""

    model_config = ConfigDict(frozen=True)

    unit_id: str

    default: AttackSlot | None = None
    counter: AttackSlot | None = None
    alt: AttackSlot | None = None
    alt2: AttackSlot | None = None


class Unit(BaseModel):
    """One unit (creature) in Olden Era."""

    model_config = ConfigDict(frozen=True)

    # Identity
    id: str
    faction: Faction
    tier: int

    # Provenance
    source_path: str

    # Localization slots
    name_sid: Sid = Field(description="Convention: <id>_name.")
    narrative_description_sid: Sid | None = None
    base_sid: Sid | None = None
    upgrade_sid: Sid | None = None

    # Combat / economy
    stats: UnitStats
    raw_stats: dict[str, Any] = {}
    cost: tuple[ResourceCost, ...] = ()

    # Attack blocks (opaque dicts kept for diff visibility)
    default_attacks: tuple[dict[str, Any], ...] = ()
    counter_attacks: tuple[dict[str, Any], ...] = ()
    alternative_attacks: tuple[dict[str, Any], ...] = ()

    # Raw JSON blocks (kept for diff engine, not directly emitted)
    raw_passives: tuple[dict[str, Any], ...] = ()
    raw_conditional_passives: tuple[dict[str, Any], ...] = ()
    raw_global_passives: tuple[dict[str, Any], ...] = ()
    raw_abilities: tuple[dict[str, Any], ...] = ()
    aura: dict[str, Any] | None = None

    # Consolidated ability/passive rows
    unit_abilities: tuple[UnitAbility, ...] = ()

    # Per-unit attack record (D-021)
    unit_attack: UnitAttack | None = None

    # Creature classification
    creature_type: str | None = None
    immunities: tuple[str, ...] = ()
    disablers: tuple[str, ...] = ()
    shared_abilities: tuple[str, ...] = ()

    # Tags / classification
    native_biome: str | None = None
    ai_archetype: str | None = None
    tags: tuple[str, ...] = ()
    leave_corpse: bool | None = None

    # Misc raw fields preserved for diff visibility
    squad_value: int | None = None
    exp_bonus: int | None = None

    # Deprecated content the game ships rows for but never displays.
    unused: bool = False
