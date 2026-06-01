"""Skill-roll page emitters.

Per the skill-roll design (decisions.md D-041) the extraction produces
five Cargo tables; this module renders them onto the corresponding wiki
pages:

* ``Data:SkillRollTable/<id>`` — 24 pages, one per (faction, classType,
  mode). Each carries the header ``{{SkillRollTableDef}}`` row plus all
  ``{{SkillRollWeightDef}}`` rows for that table.
* ``Data:SkillRollBand/<band_kind>`` — 4 pages, one per band. Reference
  data; emitted once per extract.
* ``Data:StatBonusRoll/<pseudo_id>`` — 12 pages, one per pseudo-skill.
  Each carries the ``{{StatBonusRollDef}}`` row + a ``{{TranslationDef
  type='stat_bonus_roll'}}`` block for the per-pseudo desc (and the
  shared name).
* ``Data:SkillRollReplacement/<hero_id>`` — 28 pages, one per hero that
  has at least one arena overlay row.

The page layout mirrors the existing Skill / AttackPassive emit
conventions: one bot-managed comment header, then deterministic
parameter-ordered template invocations. Sparse semantics throughout —
absent fields don't emit (per D-013).
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from obelisk.emit.cargo import render_call
from obelisk.emit.unit import render_translation_block
from obelisk.models.localization import LocalizationCorpus
from obelisk.models.skill_roll import (
    BAND_KINDS,
    SkillRollBandRecord,
    SkillRollReplacementRecord,
    SkillRollTableRecord,
    SkillRollWeightRecord,
    StatBonusRollRecord,
)
from obelisk.resolve import PlaceholderResolver


# Field orders (match the schema docs verbatim).
_TABLE_FIELD_ORDER: tuple[str, ...] = (
    "id", "class_id", "faction", "class_type", "mode", "source_path",
)

_WEIGHT_FIELD_ORDER: tuple[str, ...] = (
    "table_id", "band_kind", "skill_id", "weight",
)

_BAND_FIELD_ORDER: tuple[str, ...] = ("id", "levels", "description")

_STAT_BONUS_FIELD_ORDER: tuple[str, ...] = (
    "id", "stat", "magnitude", "weight", "name_sid", "desc_sid",
)

_REPLACEMENT_FIELD_ORDER: tuple[str, ...] = (
    "hero_id", "arena_table_id", "level", "skill_id", "weight",
)


# ----------------------------------------------------------------------------
# SkillRollTable + its weights (the bulk of the per-class data)
# ----------------------------------------------------------------------------

def _render_table_header(table: SkillRollTableRecord) -> str:
    return render_call(
        "SkillRollTableDef",
        {
            "id": table.id,
            "class_id": table.class_id,
            "faction": table.faction,
            "class_type": table.class_type,
            "mode": table.mode,
            "source_path": table.source_path,
        },
        key_order=_TABLE_FIELD_ORDER,
    )


def _render_weight(w: SkillRollWeightRecord) -> str:
    return render_call(
        "SkillRollWeightDef",
        {
            "table_id": w.table_id,
            "band_kind": w.band_kind,
            "skill_id": w.skill_id,
            "weight": w.weight,
        },
        key_order=_WEIGHT_FIELD_ORDER,
    )


def _band_sort_index(band_kind: str) -> int:
    try:
        return BAND_KINDS.index(band_kind)
    except ValueError:
        return 99


def emit_skill_roll_table_page(
    table: SkillRollTableRecord,
    weights: Iterable[SkillRollWeightRecord],
) -> str:
    """Render one ``Data:SkillRollTable/<id>`` page.

    ``weights`` is the iterable of SkillRollWeightRecord rows where
    ``table_id == table.id``. Caller filters.

    Output order: header first, then weights grouped by band_kind (in the
    canonical BAND_KINDS order: default, magic_levels, signature_levels,
    level_20_mega), then by weight DESC, then by skill_id ASC. Stable
    across runs so the diff engine sees real changes only.
    """
    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        _render_table_header(table),
    ]
    sorted_weights = sorted(
        weights,
        key=lambda w: (_band_sort_index(w.band_kind), -w.weight, w.skill_id),
    )
    for w in sorted_weights:
        blocks.append(_render_weight(w))
    return "\n\n".join(blocks) + "\n"


# ----------------------------------------------------------------------------
# SkillRollBand (4 shared rows)
# ----------------------------------------------------------------------------

def emit_skill_roll_band_page(band: SkillRollBandRecord) -> str:
    """Render one ``Data:SkillRollBand/<band_kind>`` page.

    Reference data — the level grid plus a human-readable description.
    Description currently extractor-supplied; wiki editors may revise
    it in place (the diff engine will surface re-extracted defaults as
    changes only when the source design actually shifts)."""
    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        render_call(
            "SkillRollBandDef",
            {
                "id": band.id,
                "levels": band.levels,
                "description": band.description,
            },
            key_order=_BAND_FIELD_ORDER,
        ),
    ]
    return "\n\n".join(blocks) + "\n"


# ----------------------------------------------------------------------------
# StatBonusRoll (12 pseudo-skill rows; the universal -2 fallback pool)
# ----------------------------------------------------------------------------

def emit_stat_bonus_roll_page(
    row: StatBonusRollRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render one ``Data:StatBonusRoll/<pseudo_id>`` page.

    Carries the structural ``{{StatBonusRollDef}}`` row plus a
    ``{{TranslationDef type='stat_bonus_roll'}}`` block that holds the
    per-pseudo description text in every language. The name_sid is
    shared across all 12 (``skill_pseudo_name``) so its text duplicates
    on every page's Translation rows — accepted redundancy; matches the
    source data and keeps the per-row query path uniform.
    """
    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        render_call(
            "StatBonusRollDef",
            {
                "id": row.id,
                "stat": row.stat,
                "magnitude": row.magnitude,
                "weight": row.weight,
                "name_sid": row.name_sid,
                "desc_sid": row.desc_sid,
            },
            key_order=_STAT_BONUS_FIELD_ORDER,
        ),
    ]
    xlat = render_translation_block(
        translation_type="stat_bonus_roll",
        target_id=row.id,
        name_sid=row.name_sid,
        desc_sid=row.desc_sid,
        corpus=corpus,
        resolver=resolver,
    )
    if xlat:
        blocks.append(xlat)
    return "\n\n".join(blocks) + "\n"


# ----------------------------------------------------------------------------
# SkillRollReplacement (per-hero arena overlays; ~28 pages)
# ----------------------------------------------------------------------------

def emit_skill_roll_replacement_page(
    hero_id: str,
    rows: Iterable[SkillRollReplacementRecord],
) -> str:
    """Render one ``Data:SkillRollReplacement/<hero_id>`` page.

    Inlines every replacement row for the hero (typically 3 rows, one
    per arena level 2/4/6). Sorted by (level, skill_id) for stability.
    """
    sorted_rows = sorted(rows, key=lambda r: (r.level, r.skill_id))
    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
    ]
    for r in sorted_rows:
        blocks.append(render_call(
            "SkillRollReplacementDef",
            {
                "hero_id": r.hero_id,
                "arena_table_id": r.arena_table_id,
                "level": r.level,
                "skill_id": r.skill_id,
                "weight": r.weight,
            },
            key_order=_REPLACEMENT_FIELD_ORDER,
        ))
    return "\n\n".join(blocks) + "\n"


# ----------------------------------------------------------------------------
# Convenience: group weights / replacements by their parent key
# ----------------------------------------------------------------------------

def group_weights_by_table(
    weights: Iterable[SkillRollWeightRecord],
) -> dict[str, list[SkillRollWeightRecord]]:
    out: dict[str, list[SkillRollWeightRecord]] = {}
    for w in weights:
        out.setdefault(w.table_id, []).append(w)
    return out


def group_replacements_by_hero(
    replacements: Iterable[SkillRollReplacementRecord],
) -> dict[str, list[SkillRollReplacementRecord]]:
    out: dict[str, list[SkillRollReplacementRecord]] = {}
    for r in replacements:
        out.setdefault(r.hero_id, []).append(r)
    return out
