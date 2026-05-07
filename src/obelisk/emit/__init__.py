"""Emitter — turn canonical records into wikitext."""

from obelisk.emit.cargo import block_hash, render_call
from obelisk.emit.faction import emit_faction_page
from obelisk.emit.hero import (
    emit_hero_class_page,
    emit_hero_page,
    emit_hero_specialization_page,
    emit_hero_sub_class_page,
)
from obelisk.emit.artifact import emit_artifact_page
from obelisk.emit.astrologist_event import emit_astrologist_event_page
from obelisk.emit.building import emit_building_page, emit_buildings_group_page
from obelisk.emit.difficulty import emit_difficulty_page
from obelisk.emit.item_set import emit_item_set_page
from obelisk.emit.law import emit_law_page
from obelisk.emit.map_object import emit_map_object_page
from obelisk.emit.skill import emit_orphan_sub_skills_page, emit_skill_page
from obelisk.emit.spell import emit_spell_page
from obelisk.emit.unit import (
    ENTRY_SEEDS,
    emit_attack_passive_page,
    emit_entry_page,
    emit_entry_page_from_seed,
    emit_unit_page,
    iter_entry_seeds,
    render_entry_block,
    render_translation_block,
)

__all__ = [
    "ENTRY_SEEDS",
    "block_hash",
    "emit_attack_passive_page",
    "emit_entry_page",
    "emit_entry_page_from_seed",
    "emit_faction_page",
    "emit_hero_class_page",
    "emit_hero_page",
    "emit_hero_specialization_page",
    "emit_artifact_page",
    "emit_astrologist_event_page",
    "emit_building_page",
    "emit_buildings_group_page",
    "emit_difficulty_page",
    "emit_hero_sub_class_page",
    "emit_item_set_page",
    "emit_law_page",
    "emit_map_object_page",
    "emit_orphan_sub_skills_page",
    "emit_skill_page",
    "emit_spell_page",
    "emit_unit_page",
    "iter_entry_seeds",
    "render_call",
    "render_entry_block",
    "render_translation_block",
]
