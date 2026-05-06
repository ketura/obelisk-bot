"""Extraction layer — read source JSON, produce canonical pydantic records."""

from obelisk.extract.faction import extract_factions
from obelisk.extract.hero import (
    extract_hero_specializations,
    extract_hero_sub_classes,
    extract_heroes,
)
from obelisk.extract.artifact import extract_artifacts
from obelisk.extract.item_set import extract_item_sets
from obelisk.extract.spell import extract_spells
from obelisk.extract.loader import (
    CorePaths,
    iter_array,
    iter_tokens,
    load_json,
)
from obelisk.extract.localization import load_localization_corpus
from obelisk.extract.ownership import OwnershipClaims, assign_ownership
from obelisk.extract.unit import (
    UnitExtractionResult,
    extract_units,
    extract_units_enriched,
)

__all__ = [
    "CorePaths",
    "OwnershipClaims",
    "UnitExtractionResult",
    "assign_ownership",
    "extract_factions",
    "extract_hero_specializations",
    "extract_hero_sub_classes",
    "extract_artifacts",
    "extract_heroes",
    "extract_item_sets",
    "extract_spells",
    "extract_units",
    "extract_units_enriched",
    "iter_array",
    "iter_tokens",
    "load_json",
    "load_localization_corpus",
]
