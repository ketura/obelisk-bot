"""Extraction layer — read source JSON, produce canonical pydantic records."""

from artificer.extract.faction import extract_factions
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
    "extract_units",
    "extract_units_enriched",
    "iter_array",
    "iter_tokens",
    "load_json",
    "load_localization_corpus",
]
