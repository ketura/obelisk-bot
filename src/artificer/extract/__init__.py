"""Extraction layer — read source JSON, produce canonical pydantic records."""

from artificer.extract.faction import extract_factions
from artificer.extract.hero import (
    extract_hero_specializations,
    extract_hero_sub_classes,
    extract_heroes,
)
from artificer.extract.artifact import extract_artifacts
from artificer.extract.item_set import extract_item_sets
from artificer.extract.spell import extract_spells
from artificer.extract.loader import (
    CorePaths,
    iter_array,
    iter_tokens,
    load_json,
)
from artificer.extract.localization import load_localization_corpus
from artificer.extract.ownership import OwnershipClaims, assign_ownership
from artificer.extract.unit import (
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
