"""Canonical Hero / HeroClass models.

D-027: every hero record carries the per-hero data (id, icon,
specialization, list-shaped start* slots) plus *deltas* against its
parent ``HeroClass``. The 11 class-level fields (mesh, mounts,
stats, statsRolls, costGold, etc.) sparse-emit on the Hero row when
they match the class default; campaign/tutorial heroes routinely
override `stats`/`startLevel`/`attacksTimesBefore`.

The 12 ``HeroClass`` rows are derived from the 108 faction heroes
(``DB/heroes/{humans,necros,dungeon,nature,demons,unfrozen}/*.json``)
by clustering on ``(fraction, classType)`` and reading the
class-shared fields from any hero in the cell — the source data has
zero deviations within those cells.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from artificer.models.common import Sid


# -----------------------------------------------------------------------------
# Shared sub-records
# -----------------------------------------------------------------------------


class HeroStats(BaseModel):
    """Hero stat block, mirrors source ``stats`` dict.

    Source field names are camelCase; we normalize to snake_case here.
    The boolean ``enableTactics``/``enableHeroNativeBiome`` flags are
    kept because they vary by class.
    """

    model_config = ConfigDict(frozen=True)

    view_radius: int
    stats_num: int
    magic_casts_per_round: int
    enable_tactics: bool
    tactics_placement_size: int
    enable_hero_native_biome: bool
    offence: int
    defence: int
    spell_power: int
    intelligence: int
    luck: int
    morale: int


class HeroStatsRolls(BaseModel):
    """Two-band stat roll table, flattened.

    Source shape: ``[{levelFrom, rollChances: [{v, c}]}, ...]`` —
    always 2 bands × 4 chances (one per stat) across all 108 faction
    heroes in the 2026-05-03 corpus. The ``v`` indexes 0/1/2/3 are
    interpreted as attack / defense / power / knowledge in that order
    (positional; see HeroClass.md). Weights sum to 100 per band.
    """

    model_config = ConfigDict(frozen=True)

    lvl1_attack: int
    lvl1_defense: int
    lvl1_power: int
    lvl1_knowledge: int
    lvl24_attack: int
    lvl24_defense: int
    lvl24_power: int
    lvl24_knowledge: int


class HeroStartSquadSlot(BaseModel):
    """One slot in a hero's starting army.

    Source shape: ``{sid, min, max}``. ``variant`` is added by the
    extractor to distinguish primary vs alt loadouts; source has two
    parallel arrays (``startSquad`` / ``startSquadAlt``) which we
    merge into a single side table with this discriminator.
    """

    model_config = ConfigDict(frozen=True)

    variant: str  # "primary" or "alt"
    slot: int     # 1-based position within the variant
    unit_sid: Sid
    min: int
    max: int


# NOTE: starting skills and magics are stored as flat tuples of SIDs on
# HeroRecord (see below). Source data attaches `skillLevel` to each
# starting skill and `level`/`isLearned` to each starting magic; per
# D-027 (revised) we drop those — the level data is mostly constant
# (200/208 starting skills are level 1; all starting magics are level 1
# / isLearned True in the 2026-05-03 corpus). Wiki side joins to
# Skill / Spell on the SID.


# -----------------------------------------------------------------------------
# HeroClass: derived class defaults
# -----------------------------------------------------------------------------


class HeroClassRecord(BaseModel):
    """One of the 12 (faction × classType) hero classes.

    Derived from the faction-hero corpus by clustering on the
    ``(fraction, classType)`` pair — the source data has no explicit
    ``DB/heroes_classes/`` file, but every faction hero in a cell
    shares the same class-level field values, so clustering recovers
    the implicit class definition.

    The ``id`` follows the L10n SID convention:
    ``<class_type>_<fraction>`` (e.g. ``magic_demon`` → "Herald").
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name_sid: Sid
    desc_sid: Sid

    faction: str
    class_type: str  # "might" or "magic"

    mesh: str
    mount: str
    native_biome: str
    skills_roll_variant: str
    cost_gold: int
    start_level: int
    attacks_times_before: tuple[float, ...]

    stats: HeroStats
    stats_rolls: HeroStatsRolls


# -----------------------------------------------------------------------------
# Hero: per-hero record with sparse class overrides
# -----------------------------------------------------------------------------


class HeroRecord(BaseModel):
    """One hero. Mirrors the source JSON with normalized field names
    and class-default fields encoded as sparse overrides.

    For faction heroes (108), the override fields below are all
    ``None`` (they match the class default). For campaign and
    tutorial heroes (67), some of the override fields will be set —
    typically ``stats_override``, ``start_level_override``,
    ``attacks_times_before_override``.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name_sid: Sid     # source ``name`` (faction heroes implicit = id; campaign explicit)
    motto_sid: Sid    # source ``motto`` (faction heroes implicit = id+"_motto")
    desc_sid: Sid     # source ``description`` (faction heroes implicit = id+"_description")

    class_id: str     # joins HeroClassRecord.id (e.g. "magic_demon")
    faction: str      # denormalized from class for filter convenience
    class_type: str   # ditto

    icon: str
    specialization_id: str

    source_path: str

    # List-shaped per-hero data (always per-hero, never class-default).
    start_squad: tuple[HeroStartSquadSlot, ...]
    # Starting skills: tuple of (sid, level) pairs. Emitted as two
    # parallel List columns on the Hero row (start_skills +
    # start_skill_levels). Per D-027 (revised twice): level mostly 1
    # but 8/208 entries are level 2 — preserved.
    start_skills: tuple[tuple[Sid, int], ...]
    # Starting spells: flat tuple of SIDs. Level / isLearned dropped
    # (constant in 2026-05-03 corpus). Wiki joins to future Spell.
    start_magics: tuple[Sid, ...]

    # Class-default overrides (sparse: None means inherit from HeroClass).
    cost_gold_override: int | None = None
    start_level_override: int | None = None
    attacks_times_before_override: tuple[float, ...] | None = None
    mesh_override: str | None = None
    mount_override: str | None = None
    native_biome_override: str | None = None
    skills_roll_variant_override: str | None = None
    stats_override: HeroStats | None = None
    stats_rolls_override: HeroStatsRolls | None = None


# -----------------------------------------------------------------------------
# HeroSpecialization
# -----------------------------------------------------------------------------


class Bonus(BaseModel):
    """One bonus effect.

    Per D-031, a single shape covers bonuses for hero specializations,
    hero sub-classes, items, and any future entity that uses the same
    ``{type, parameters, [activationLevel], [upgrade], [receivers],
    [battleType], [receiverRole], [receiverAllegiance]}`` source pattern.
    Discriminator columns ``parent_type`` and ``parent_id`` identify
    which parent entity the bonus belongs to.
    """

    model_config = ConfigDict(frozen=True)

    parent_type: str  # e.g. hero_specialization, hero_sub_class, item
    parent_id: str
    ordinal: int  # 0-based position within the parent's bonuses[]
    type: str
    parameters: tuple[str, ...]
    activation_level: int | None = None
    upgrade_increment: float | None = None
    upgrade_level_step: int | None = None
    receivers: tuple[Sid, ...] = ()
    battle_type: str | None = None
    receiver_role: str | None = None
    receiver_allegiance: str | None = None


# Backward-compat alias — extract code may still reference the old name.
HeroSpecializationBonus = Bonus
HeroSubClassBonus = Bonus


class HeroSpecializationRecord(BaseModel):
    """A hero's unique passive specialization. 1:1 with each Hero —
    every faction/campaign/tutorial hero has exactly one
    specialization that makes them mechanically distinct.

    ``raw_json`` retains the source JSON dict so the placeholder
    resolver can satisfy ``CurrentHeroSpecializationConfig`` reads
    (paths like ``bonuses[0].parameters[1]``) when emitting the
    spec's localized description text.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name_sid: Sid
    desc_sid: Sid
    icon: str
    bonuses: tuple[Bonus, ...]
    source_path: str
    raw_json: dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# HeroSubClass
# -----------------------------------------------------------------------------


# NOTE: HeroSubClassBonus folded into the unified Bonus class per
# D-031 (revised D-029). The old HeroSubClassBonus name is kept as
# an alias above for backward compatibility during the transition.


class HeroSubClassRecord(BaseModel):
    """A named prestige class (Swashbuckler, Paragon, Grand Inquisitor,
    Ascendant, etc.) unlocked when a hero hits 5 specific skill
    thresholds. Always 4 per (faction × class_type) cell — the 2 might
    sub-classes for might heroes, 2 magic for magic. See D-029.

    Activation conditions are flattened to 5 (sid, level) pairs as
    inline columns; ``subSkillSids`` (always empty in the 2026-05-03
    corpus) is dropped per editor preference.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name_sid: Sid
    desc_sid: Sid
    icon: str
    faction: str
    class_type: str  # "might" or "magic"

    # Five activation conditions, flattened. Always present in the
    # 2026-05-03 corpus (every sub-class has exactly 5). Each pair
    # references a Skill SID + threshold level the hero must hit.
    activation_skill_1_sid: Sid
    activation_skill_1_level: int
    activation_skill_2_sid: Sid
    activation_skill_2_level: int
    activation_skill_3_sid: Sid
    activation_skill_3_level: int
    activation_skill_4_sid: Sid
    activation_skill_4_level: int
    activation_skill_5_sid: Sid
    activation_skill_5_level: int

    bonuses: tuple[Bonus, ...]
    source_path: str


# -----------------------------------------------------------------------------
# Extraction result wrappers
# -----------------------------------------------------------------------------


class HeroExtractionResult(BaseModel):
    """Outcome of a hero-extraction run."""

    model_config = ConfigDict(frozen=True)

    hero_classes: tuple[HeroClassRecord, ...]
    heroes: tuple[HeroRecord, ...]


class HeroSpecializationExtractionResult(BaseModel):
    """Outcome of a hero-specialization-extraction run."""

    model_config = ConfigDict(frozen=True)

    specializations: tuple[HeroSpecializationRecord, ...]


class HeroSubClassExtractionResult(BaseModel):
    """Outcome of a hero-sub-class-extraction run."""

    model_config = ConfigDict(frozen=True)

    sub_classes: tuple[HeroSubClassRecord, ...]
