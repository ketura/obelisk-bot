"""Canonical record types — pydantic models that mirror the structured data we extract."""

from artificer.models.common import (
    Faction,
    ResourceCost,
    Sid,
    SidRef,
)
from artificer.models.faction import FactionRecord
from artificer.models.hero import (
    Bonus,
    HeroClassRecord,
    HeroExtractionResult,
    HeroRecord,
    HeroSpecializationBonus,  # backward-compat alias for Bonus
    HeroSpecializationExtractionResult,
    HeroSpecializationRecord,
    HeroStartSquadSlot,
    HeroStats,
    HeroStatsRolls,
    HeroSubClassBonus,  # backward-compat alias for Bonus
    HeroSubClassExtractionResult,
    HeroSubClassRecord,
)
from artificer.models.artifact import (
    ArtifactExtractionResult,
    ArtifactRecord,
)
from artificer.models.item_set import (
    ItemSetExtractionResult,
    ItemSetRecord,
    ItemSetTierRecord,
)
from artificer.models.spell import (
    SpellExtractionResult,
    SpellRankRecord,
    SpellRecord,
)
from artificer.models.localization import (
    SUPPORTED_LANGUAGES,
    LocalizationCorpus,
    LocalizationEntry,
)
from artificer.models.unit import (
    AttackSlot,
    Unit,
    UnitAbility,
    UnitAttack,
    UnitStats,
)

__all__ = [
    "SUPPORTED_LANGUAGES",
    "ArtifactExtractionResult",
    "ArtifactRecord",
    "AttackSlot",
    "Bonus",
    "Faction",
    "FactionRecord",
    "HeroClassRecord",
    "HeroExtractionResult",
    "HeroRecord",
    "HeroSpecializationBonus",
    "HeroSpecializationExtractionResult",
    "HeroSpecializationRecord",
    "HeroStartSquadSlot",
    "HeroStats",
    "HeroStatsRolls",
    "HeroSubClassBonus",
    "HeroSubClassExtractionResult",
    "HeroSubClassRecord",
    "ItemSetExtractionResult",
    "ItemSetRecord",
    "ItemSetTierRecord",
    "LocalizationCorpus",
    "LocalizationEntry",
    "ResourceCost",
    "Sid",
    "SidRef",
    "SpellExtractionResult",
    "SpellRankRecord",
    "SpellRecord",
    "Unit",
    "UnitAbility",
    "UnitAttack",
    "UnitStats",
]
