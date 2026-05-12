"""Emitter — turn canonical records into wikitext."""

from obelisk.emit.cargo import block_hash, render_call


# Wiki-side category attached to every bot-emitted data page. Lets
# wiki editors find/audit/filter the entire bot-managed corpus with
# a single Cargo or Special:Categories query. The index pages
# (Data:<Table>) use a separate ``[[Category:Game Data Indices]]`` —
# see ``emit/index.py``.
DATA_IMPORT_CATEGORY = "Game Data Import"


def with_import_category(page: str) -> str:
    """Append the ``[[Category:Game Data Import]]`` tag to a page.

    Idempotent — pages that already carry the category line through
    them unchanged, so emit functions that opt into the category at
    construction time (or test fixtures that bake it in) don't get a
    duplicate tag appended.

    The category is separated from the prior content by a blank line
    so the wiki source renders cleanly regardless of whether the
    upstream page ended with ``}}``, a bullet list, or anything else.
    """
    tag = f"[[Category:{DATA_IMPORT_CATEGORY}]]"
    if tag in page:
        return page
    # Trim only trailing whitespace — preserve any leading blank line
    # the emit function may have included for formatting.
    body = page.rstrip()
    return f"{body}\n\n{tag}\n"
from obelisk.emit.faction import emit_faction_page
from obelisk.emit.index import (
    INDEX_FILENAME,
    load_index_blurbs,
    render_index_page,
    write_index_pages,
)
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
    "DATA_IMPORT_CATEGORY",
    "ENTRY_SEEDS",
    "INDEX_FILENAME",
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
    "load_index_blurbs",
    "render_call",
    "render_entry_block",
    "render_index_page",
    "render_translation_block",
    "with_import_category",
    "write_index_pages",
]
