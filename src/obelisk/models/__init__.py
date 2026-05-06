"""Canonical record types — pydantic models that mirror the structured data we extract."""

from obelisk.models.common import (
    Faction,
    ResourceCost,
    Sid,
    SidRef,
)
from obelisk.models.faction import FactionRecord
from obelisk.models.hero import (
    Bonus,
    HeroClassRecord,
    HeroExtractionResult,
    HeroRecord,
    HeroSpecializationBonus,
    HeroSpecializationExtractionResult,
    HeroSpecializationRecord,
    HeroStartSquadSlot,
    HeroStats,
    HeroStatsRolls,
    HeroSubClassBonus,
    HeroSubClassExtractionResult,
    HeroSubClassRecord,
)
from obelisk.models.artifact import (
    ArtifactExtractionResult,
    ArtifactRecord,
)
from obelisk.models.item_set import (
    ItemSetExtractionResult,
    ItemSetRecord,
    ItemSetTierRecord,
)
from obelisk.models.law import (
    FactionLawTierRecord,
    LawExtractionResult,
    LawLevelRecord,
    LawRecord,
    LawTreePositionRecord,
)
from obelisk.models.spell import (
    SpellExtractionResult,
    SpellRankRecord,
    SpellRecord,
)
from obelisk.models.localization import (
    SUPPORTED_LANGUAGES,
    LocalizationCorpus,
    LocalizationEntry,
)
from obelisk.models.unit import (
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
    "FactionLawTierRecord",
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
    "LawExtractionResult",
    "LawLevelRecord",
    "LawRecord",
    "LawTreePositionRecord",
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
