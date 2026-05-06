"""Canonical Spell / SpellRank models.

Per D-030: each spell has a base record (Spell) plus 4 SpellRank
side rows — one per mastery level (1=no skill, 2=basic, 3=advanced,
4=expert). The level-indexed source arrays (`description`,
`manaCost`) split out across SpellRank rows; the level-up bonus
data (`bonusDescriptions[]`, `upgradeCost[]`) attaches to the
SpellRank for the level being unlocked (so SpellRank for level 1
has no bonus_description / upgrade_cost; the rest do).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from obelisk.models.common import Sid


class SpellRankRecord(BaseModel):
    """Per-mastery-level data for a spell.

    The 4 levels correspond to the hero's skill in the spell's
    school: 1=no skill, 2=basic, 3=advanced, 4=expert. Levels 2/3/4
    additionally carry the unlock-bonus description (the text that
    explains what's new at this rank) and the upgrade cost paid to
    reach this level.
    """

    model_config = ConfigDict(frozen=True)

    spell_id: str
    level: int  # 1..4

    description_sid: Sid | None = None
    description: str | None = None  # resolved English

    mana_cost: int | None = None

    # Level-up bonus + upgrade cost (None for level 1)
    bonus_description_sid: Sid | None = None
    bonus_description: str | None = None
    upgrade_cost: int | None = None


class SpellRecord(BaseModel):
    """A single spell. Carries identity + classification + the four
    learn-cost resource columns. Per-mastery data lives in 4 paired
    :class:`SpellRankRecord` instances.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name_sid: Sid
    icon: str

    school: str  # day, night, primal, space, neutral
    rank: int    # 1..5
    used_on_map: bool

    magic_type_description: Sid | None = None  # SID for the type label

    # Special-magic flags
    is_special_magic: bool = False
    is_unique_magic: bool = False
    normal_magic_sid: Sid | None = None  # back-ref for is_special_magic spells

    # Learn cost split by resource (sparse — zero/missing → omitted)
    learn_cost_gemstones: int | None = None
    learn_cost_crystals: int | None = None
    learn_cost_mercury: int | None = None
    learn_cost_star_dust: int | None = None

    # Optional flags + sparse fields
    excaption_in_tooltip_sid: Sid | None = None
    up_effect_description_sid: Sid | None = None
    use_expand_tooltip: bool | None = None
    energy_cost: int | None = None
    energy_type: str | None = None

    ranks: tuple[SpellRankRecord, ...]
    source_path: str

    # Source JSON kept for placeholder resolver context
    # (CurrentMagicBattle reads battleMagic.targetMechanics paths).
    raw_json: dict[str, Any] = Field(default_factory=dict)


class SpellExtractionResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    spells: tuple[SpellRecord, ...]
