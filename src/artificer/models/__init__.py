"""Canonical record types — pydantic models that mirror the structured data we extract."""

from artificer.models.common import (
    Faction,
    ResourceCost,
    Sid,
    SidRef,
)
from artificer.models.faction import FactionRecord
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
    "AttackSlot",
    "Faction",
    "FactionRecord",
    "LocalizationCorpus",
    "LocalizationEntry",
    "ResourceCost",
    "Sid",
    "SidRef",
    "Unit",
    "UnitAbility",
    "UnitAttack",
    "UnitStats",
]
