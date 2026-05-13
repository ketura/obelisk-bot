"""Extraction layer — read source JSON, produce canonical pydantic records."""

from obelisk.extract.difficulty import extract_difficulties
from obelisk.extract.faction import extract_factions
from obelisk.extract.hero import (
    apply_skill_granted_magics,
    apply_specialization_magic_replacements,
    extract_hero_specializations,
    extract_hero_sub_classes,
    extract_heroes,
)
from obelisk.extract.artifact import extract_artifacts
from obelisk.extract.astrologist_event import extract_astrologist_events
from obelisk.extract.building import extract_buildings
from obelisk.extract.item_set import extract_item_sets
from obelisk.extract.law import extract_laws
from obelisk.extract.map_object import extract_map_objects
from obelisk.extract.resource import extract_resources
from obelisk.extract.skill import extract_skills
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
    "apply_skill_granted_magics",
    "apply_specialization_magic_replacements",
    "assign_ownership",
    "extract_artifacts",
    "extract_astrologist_events",
    "extract_buildings",
    "extract_difficulties",
    "extract_factions",
    "extract_hero_specializations",
    "extract_hero_sub_classes",
    "extract_heroes",
    "extract_item_sets",
    "extract_laws",
    "extract_map_objects",
    "extract_resources",
    "extract_skills",
    "extract_spells",
    "extract_units",
    "extract_units_enriched",
    "iter_array",
    "iter_tokens",
    "load_json",
    "load_localization_corpus",
]
