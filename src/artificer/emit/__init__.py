"""Emitter — turn canonical records into wikitext."""

from artificer.emit.cargo import block_hash, render_call
from artificer.emit.unit import (
    ATTACK_ARCHETYPE_SEEDS,
    emit_attack_archetype_page,
    emit_attack_passive_page,
    emit_unit_page,
)

__all__ = [
    "ATTACK_ARCHETYPE_SEEDS",
    "block_hash",
    "emit_attack_archetype_page",
    "emit_attack_passive_page",
    "emit_unit_page",
    "render_call",
]
