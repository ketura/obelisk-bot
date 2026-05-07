"""Canonical Skill / SkillLevel / SubSkill models.

Per D-037: hero skill tree data lives in three layers —

* ``Skill`` — top-level skill entity (e.g. ``skill_assault``,
  ``arena_skill_assault``, ``campaign_skill_assault``,
  ``skill_pseudo_1``). 102 entries: 30 production + 12 pseudo +
  30 arena + 30 campaign.
* ``SkillLevel`` — per-(skill, level) row, ~270 total. Source's
  ``parametersPerLevel`` flattened by level (typically 3 levels
  per real skill, 1 for pseudo). Carries that level's
  name/desc/icon override and the list of sub-skills it offers.
* ``SubSkill`` — flat per-sub-skill record, ~617 total: 203 prod
  + 203 arena + 203 campaign + 8 test. Each carries identity +
  bonuses (no levels). Linked to a parent skill via the
  scanning of skill-level ``subSkills[]`` lists.

Bonuses for both layers flow through the unified ``Bonus`` table
with ``parent_type='skill_level'`` (parent_id ``<skill_id>_L<level>``)
and ``parent_type='sub_skill'`` (parent_id ``<sub_skill_id>``).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from obelisk.models.common import Sid
from obelisk.models.hero import Bonus


class SkillLevelRecord(BaseModel):
    """One mastery level of a skill.

    Sourced from one element of the parent skill's
    ``parametersPerLevel`` array. Carries the level-specific name +
    desc + icon overrides plus the bonuses that take effect at this
    level. ``offered_sub_skills`` is the list of sub-skill ids the
    player can pick at this level.
    """

    model_config = ConfigDict(frozen=True)

    skill_id: str
    level: int  # 1-based
    name_sid: Sid | None = None
    desc_sid: Sid | None = None
    icon: str | None = None
    offered_sub_skills: tuple[str, ...] = ()
    bonuses: tuple[Bonus, ...] = ()
    raw_json: dict[str, Any] = Field(default_factory=dict)


class SkillRecord(BaseModel):
    """One hero skill.

    ``variant`` distinguishes production / arena / campaign /
    pseudo variants of the same skill family (e.g. ``skill_assault``
    vs ``arena_skill_assault``). ``skill_type`` is one of
    ``Common`` / ``Class`` / ``Faction``; pseudo skills have no
    skill_type.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    variant: str  # production / arena / campaign / pseudo
    skill_type: str | None = None  # Common / Class / Faction
    is_pseudo: bool = False
    name_sid: Sid
    desc_sid: Sid | None = None
    levels: tuple[SkillLevelRecord, ...]
    source_path: str


class SubSkillRecord(BaseModel):
    """One flat sub-skill ("perk") record.

    ``parent_skill_id`` is derived: the parent skill whose
    ``parametersPerLevel[N].subSkills[]`` lists this sub-skill.
    Unreferenced sub-skills (the 8 test orphans) get
    ``parent_skill_id=None`` and live on the catch-all page.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    variant: str  # production / arena / campaign / test
    parent_skill_id: str | None = None
    name_sid: Sid
    desc_sid: Sid | None = None
    icon: str | None = None
    bonuses: tuple[Bonus, ...] = ()
    source_path: str
    raw_json: dict[str, Any] = Field(default_factory=dict)


class SkillExtractionResult(BaseModel):
    """All skill-related rows produced from a single patch extract."""

    model_config = ConfigDict(frozen=True)

    skills: tuple[SkillRecord, ...]
    sub_skills: tuple[SubSkillRecord, ...]
