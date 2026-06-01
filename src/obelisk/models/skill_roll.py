"""Canonical skill-roll table records.

Per the skill-roll design (see decisions.md D-041) the hero level-up skill
roll system decomposes into five tables that map back to two source dirs:

* ``Core/DB/heroes_skills/skills_by_level_tables/*.json`` — 24 standard +
  arena tables, each with a ``defaultList`` and a ``specialList``.
* ``Core/DB/heroes_skills/skills_by_level_replace_tables/skills_by_level_replace_table.json``
  — 28 hero-specific arena overlays.
* ``Core/DB/heroes_skills/skills/pseudo_skills.json`` — 12 pseudo skills
  (the +N stat bonuses used as the engine's fallback pool).

Ground-truth tiering on the source data:

* The ``[-1]`` sentinel band is byte-identical to the ``[1..50]`` default
  in every observed file — a suspected engine fallback for an unreachable
  code path. The extractor drops it and audits divergence if any future
  patch breaks the equality.
* The ``[-2]`` band is byte-identical across all 24 files — the engine's
  pseudo-skill fallback pool. Extracted once into ``StatBonusRollRecord``;
  not stored per-table.
* The default ``[1..50]`` band and the ``specialList`` entries become
  ``SkillRollWeightRecord`` rows with explicit ``band_kind`` discriminators
  (``default`` / ``magic_levels`` / ``signature_levels`` / ``level_20_mega``).
  The level grid is class-invariant and lives in ``SkillRollBandRecord``.

Bands are *additive*: at level L, the effective weight for skill S is the
sum of weights across every band whose ``levels`` list contains L. The
``[-2]`` fallback is gated on hero state (only fires when the main pool
can't supply 3 valid offerings), not on level.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from obelisk.models.common import Sid


# Canonical band-kind discriminator. The ordering here is also the
# emit order — ``default`` first, then the milestone overlays.
BAND_KINDS: tuple[str, ...] = (
    "default",
    "magic_levels",
    "signature_levels",
    "level_20_mega",
)


class SkillRollTableRecord(BaseModel):
    """One skill-roll table header.

    24 in total: 12 standard ``<faction>_<class>_skills_table`` plus 12
    arena counterparts. The per-skill weights live in
    ``SkillRollWeightRecord`` rows joined by ``table_id``.

    ``class_id`` is the canonical HeroClass id (``<class_type>_<faction>``,
    e.g. ``might_human``) — kept alongside ``faction`` / ``class_type`` for
    bidirectional join convenience with the ``HeroClass`` table.
    """

    model_config = ConfigDict(frozen=True)

    id: str            # source-JSON id, e.g. ``humans_might_skills_table``
    class_id: str      # canonical HeroClass id, e.g. ``might_human``
    faction: str       # human / undead / dungeon / nature / demon / unfrozen
    class_type: str    # might / magic
    mode: str          # standard / arena
    source_path: str


class SkillRollWeightRecord(BaseModel):
    """One (table, band_kind, skill) weight row.

    All weights are integers from the source's ``chance`` field. Raw,
    additive across bands. Lives in the unified ``SkillRollWeight`` Cargo
    table.
    """

    model_config = ConfigDict(frozen=True)

    table_id: str
    band_kind: str  # one of BAND_KINDS
    skill_id: str   # skill SID (joins to Skill.id)
    weight: int


class SkillRollBandRecord(BaseModel):
    """Reference-data row mapping a ``band_kind`` to its level grid.

    Class-invariant — 4 rows total. ``levels`` is the tuple of integer
    levels at which the band fires; Cargo stores it as a comma-joined
    ``List of Integer`` so ``HOLDS`` works in queries.
    """

    model_config = ConfigDict(frozen=True)

    id: str                       # one of BAND_KINDS
    levels: tuple[int, ...]       # sorted ascending
    description: str              # human-readable trigger explanation


class StatBonusRollRecord(BaseModel):
    """One pseudo-skill row from the universal ``[-2]`` fallback pool.

    12 rows total. Each row grants ``magnitude`` to one ``stat``
    (offence / defence / spellPower / intelligence). ``weight`` is the
    raw chance value the engine draws against when the main skill pool
    can't supply a valid offering.

    The 12 rows share a single ``name_sid`` (``skill_pseudo_name``); the
    ``desc_sid`` is per-row (``skill_pseudo_<N>_desc``).
    """

    model_config = ConfigDict(frozen=True)

    id: str           # skill_pseudo_1 .. skill_pseudo_12
    stat: str         # offence / defence / spellPower / intelligence
    magnitude: int    # 1 / 2 / 3
    weight: int       # 50000 / 500 / 5 in the observed corpus
    name_sid: Sid
    desc_sid: Sid


class SkillRollReplacementRecord(BaseModel):
    """One per-hero arena overlay row.

    Source stores levels as a list within one entry per hero; the
    extractor expands those into one row per (hero, level).
    ``arena_table_id`` is derived from the hero's faction + class_type
    (always points at an arena-mode ``SkillRollTable``).
    """

    model_config = ConfigDict(frozen=True)

    hero_id: str
    arena_table_id: str
    level: int
    skill_id: str   # arena_skill_*
    weight: int


class SkillRollExtractionResult(BaseModel):
    """All skill-roll records produced from one patch extract.

    The ``-1`` sentinel band is dropped at extract time with optional
    audit warnings. The ``[-2]`` band becomes ``stat_bonus_rolls`` (not
    stored per-table). The active bands (default + specialList) become
    ``weights`` rows under their ``band_kind`` discriminator.
    """

    model_config = ConfigDict(frozen=True)

    tables: tuple[SkillRollTableRecord, ...]
    weights: tuple[SkillRollWeightRecord, ...]
    bands: tuple[SkillRollBandRecord, ...]
    stat_bonus_rolls: tuple[StatBonusRollRecord, ...]
    replacements: tuple[SkillRollReplacementRecord, ...]
    audit_warnings: tuple[str, ...] = ()
