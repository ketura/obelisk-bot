"""Emitter — turn canonical records into wikitext."""

from artificer.emit.cargo import block_hash, render_call
from artificer.emit.faction import emit_faction_page
from artificer.emit.hero import (
    emit_hero_class_page,
    emit_hero_page,
    emit_hero_specialization_page,
    emit_hero_sub_class_page,
)
from artificer.emit.artifact import emit_artifact_page
from artificer.emit.item_set import emit_item_set_page
from artificer.emit.spell import emit_spell_page
from artificer.emit.unit import (
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
    "emit_hero_sub_class_page",
    "emit_item_set_page",
    "emit_spell_page",
    "emit_unit_page",
    "iter_entry_seeds",
    "render_call",
    "render_entry_block",
    "render_translation_block",
]
