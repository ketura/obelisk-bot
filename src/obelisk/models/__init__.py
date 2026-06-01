"""Canonical record types — pydantic models that mirror the structured data we extract."""

from obelisk.models.common import (
    Faction,
    ResourceCost,
    Sid,
    SidRef,
)
from obelisk.models.difficulty import (
    DifficultyExtractionResult,
    DifficultyRecord,
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
from obelisk.models.astrologist_event import (
    AstrologistEventExtractionResult,
    AstrologistEventRecord,
)
from obelisk.models.building import (
    BuildingExtractionResult,
    BuildingRecord,
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
from obelisk.models.map_object import (
    MapObjectExtractionResult,
    MapObjectRecord,
)
from obelisk.models.skill import (
    SkillExtractionResult,
    SkillLevelRecord,
    SkillRecord,
    SubSkillRecord,
)
from obelisk.models.skill_roll import (
    BAND_KINDS,
    SkillRollBandRecord,
    SkillRollExtractionResult,
    SkillRollReplacementRecord,
    SkillRollTableRecord,
    SkillRollWeightRecord,
    StatBonusRollRecord,
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
    "AstrologistEventExtractionResult",
    "AstrologistEventRecord",
    "AttackSlot",
    "Bonus",
    "BuildingExtractionResult",
    "BuildingRecord",
    "DifficultyExtractionResult",
    "DifficultyRecord",
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
    "MapObjectExtractionResult",
    "MapObjectRecord",
    "ResourceCost",
    "Sid",
    "SidRef",
    "BAND_KINDS",
    "SkillExtractionResult",
    "SkillLevelRecord",
    "SkillRecord",
    "SkillRollBandRecord",
    "SkillRollExtractionResult",
    "SkillRollReplacementRecord",
    "SkillRollTableRecord",
    "SkillRollWeightRecord",
    "StatBonusRollRecord",
    "SpellExtractionResult",
    "SpellRankRecord",
    "SpellRecord",
    "SubSkillRecord",
    "Unit",
    "UnitAbility",
    "UnitAttack",
    "UnitStats",
]
