"""Canonical FactionLaw / LawLevel / LawTreePosition / FactionLawTier models.

Per D-033. Source folder is ``DB/fractions_laws/`` — six production
faction tables (``fractions_laws_table_<faction>.json``) plus two
test tables. Display layout (which side / slot a law occupies on
the in-game law screen) lives on a separate ``LawTreePosition`` table
sourced from each faction's ``fractionLawsLines`` block, with the
per-tier unlock thresholds factored out into ``FactionLawTier``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from obelisk.models.common import Sid
from obelisk.models.hero import Bonus


class LawLevelRecord(BaseModel):
    """One mastery level of a law.

    A law has 1-3 levels, indexed 1-based. Each level carries its own
    cost (separate from the tier-unlock threshold) and its own bonuses
    list. Description text is shared with the parent law's ``desc_sid``
    but resolves to a different string per level because the bonus
    parameters differ.

    ``raw_json`` retains the per-level dict (one element of the
    parent's ``parametersPerLevel``) so the resolver's
    ``CurrentFractionLawConfig`` op can satisfy reads like
    ``bonuses[0].parameters[1]``.
    """

    model_config = ConfigDict(frozen=True)

    law_id: str
    level: int  # 1-based
    cost: int
    bonuses: tuple[Bonus, ...]
    raw_json: dict[str, Any] = Field(default_factory=dict)


class LawRecord(BaseModel):
    """One faction law.

    Identity (id, name, desc, icon), faction membership, balance-
    relevant tier placement (1-5; null for test laws), per-level
    side-table data inline, and a ``test`` flag for laws sourced from
    the test JSON files.

    ``faction`` and ``tier`` are populated by cross-referencing each
    faction's ``fractionLawsLines`` after the law array is parsed.
    Test laws have neither.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    faction: str | None  # null for test laws
    ordinal: int  # trailing N parsed from id
    tier: int | None  # 1-5; null for test laws

    name_sid: Sid
    desc_sid: Sid
    icon: str

    levels: tuple[LawLevelRecord, ...]
    test: bool = False

    source_path: str


class LawTreePositionRecord(BaseModel):
    """One law placement in a faction's law screen.

    Sourced from ``fractionLawsLines[tier-1].groups[group_idx].laws[slot_idx]``
    on each faction's JSON. ``side`` is derived from the group index:
    ``groups[0]`` → ``"faction"``, ``groups[1]`` → ``"army"`` (matching
    the in-game column labels).

    Production laws each get exactly one row; test laws get none.
    """

    model_config = ConfigDict(frozen=True)

    faction: str
    tier: int  # 1-5
    side: str  # "faction" | "army"
    slot: int  # 0-based within (faction, tier, side)
    law_id: str


class FactionLawTierRecord(BaseModel):
    """One per (faction, tier) pair carrying the law-points unlock
    threshold for that tier. Sourced from
    ``fractionLawsLines[tier-1].countToUnlock``."""

    model_config = ConfigDict(frozen=True)

    faction: str
    tier: int  # 1-5
    count_to_unlock: int


class LawExtractionResult(BaseModel):
    """All law-related records produced from a single patch extract."""

    model_config = ConfigDict(frozen=True)

    laws: tuple[LawRecord, ...]
    tree_positions: tuple[LawTreePositionRecord, ...]
    faction_tiers: tuple[FactionLawTierRecord, ...]
