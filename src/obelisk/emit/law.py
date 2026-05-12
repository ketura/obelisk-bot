"""Per-law wikitext page renderer.

Per D-033: each ``Data:Law/<id>`` page carries a ``{{LawDef}}`` row,
a ``{{TranslationDef | type=law | …}}`` row for the shared name, then
per-level: a ``{{LawLevelDef}}`` row, a ``{{EntryDef | type=law_level
| subtype=<id> | variant=<N> | …}}`` row carrying the level's non-
English description translations, and 0+ ``{{BonusDef
| parent_type=law_level | parent_id=<id>_L<level> | …}}`` rows.

Description SIDs are shared across levels but resolve to different
strings per level because each level's bonuses[].parameters values
are different — the resolver's ``CurrentFractionLawConfig`` op reads
from per-level law_json context.

The per-level translation row used to be its own
``LawLevelTranslationDef`` table; folded into the shared ``EntryDef``
via ``(type='law_level', subtype=law_id, variant=level)``.
"""

from __future__ import annotations

from typing import Any

from obelisk.emit.cargo import render_call
from obelisk.emit.hero import render_bonus
from obelisk.emit.unit import (
    _lookup_text,
    render_entry_block,
    render_translation_block,
)
from obelisk.models.law import LawLevelRecord, LawRecord
from obelisk.models.localization import LocalizationCorpus
from obelisk.resolve import PlaceholderResolver


_LAW_FIELD_ORDER: tuple[str, ...] = (
    "id", "faction", "ordinal", "tier",
    "name", "name_sid", "desc_sid", "icon",
    "max_level", "test", "source_path",
)

_LAW_LEVEL_FIELD_ORDER: tuple[str, ...] = (
    "law_id", "level", "cost", "description",
)


def _render_level(
    law: LawRecord,
    level: LawLevelRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> str:
    """Render one {{LawLevelDef | …}} row. Builds a per-level law_json
    context (the parametersPerLevel[level-1] dict directly) so the
    interpreter's CurrentFractionLawConfig op resolves
    ``bonuses[N].parameters[M]`` reads against the right level."""
    description = _lookup_text(
        law.desc_sid, "english", corpus, resolver, None, None,
        law_json=level.raw_json,
    )
    params: dict[str, Any] = {
        "law_id": law.id,
        "level": level.level,
        "cost": level.cost,
        "description": description,
    }
    return render_call("LawLevelDef", params, key_order=_LAW_LEVEL_FIELD_ORDER)


def _render_level_translation(
    law: LawRecord,
    level: LawLevelRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> str:
    """Per-(law, level) translation row carrying the description in
    the 15 non-English locales. English description sits on the
    parent ``LawLevelDef.description`` column.

    Emits an ``EntryDef`` row with ``(type='law_level', subtype=law_id,
    variant=level)``. Law levels have no name SID — only the
    description varies per level — so name_sid stays unset.

    Returns the empty string if the law has no desc_sid (no
    translations to emit)."""
    if not law.desc_sid:
        return ""
    return render_entry_block(
        entry_type="law_level",
        subtype=law.id,
        name_sid=None,
        desc_sid=law.desc_sid,
        corpus=corpus,
        variant=str(level.level),
        resolver=resolver,
        law_json=level.raw_json,
    )


def emit_law_page(
    law: LawRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:Law/<id>``."""
    # The {{Law}} row's `name` is shared across levels — pick level 1's
    # context for the name lookup (most law names are placeholder-free
    # anyway; the context is harmless for those that aren't).
    first_level_json = law.levels[0].raw_json if law.levels else None
    en_name = _lookup_text(
        law.name_sid, "english", corpus, resolver, None, None,
        law_json=first_level_json,
    )

    main_params: dict[str, Any] = {
        "id": law.id,
        "faction": law.faction,
        "ordinal": law.ordinal,
        "tier": law.tier,
        "name": en_name,
        "name_sid": law.name_sid,
        "desc_sid": law.desc_sid,
        "icon": law.icon,
        "max_level": len(law.levels),
        "test": law.test,
        "source_path": law.source_path,
    }

    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        render_call("LawDef", main_params, key_order=_LAW_FIELD_ORDER),
    ]

    # One {{Translation | type=law}} row for the shared name. Build it
    # in the level-1 context so any (rare) name placeholders substitute.
    xlat = render_translation_block(
        translation_type="law",
        target_id=law.id,
        name_sid=law.name_sid,
        desc_sid=None,  # description varies per level — handled below
        corpus=corpus,
        resolver=resolver,
        law_json=first_level_json,
    )
    if xlat:
        blocks.append(xlat)

    # Per-level rows: structural + translation + N bonuses. The
    # translation row is skipped when the law has no desc_sid
    # (nothing to localize), which lets emit treat the absence as
    # sparse rather than emitting an empty stub.
    for level in law.levels:
        blocks.append(_render_level(law, level, corpus, resolver))
        xlat = _render_level_translation(law, level, corpus, resolver)
        if xlat:
            blocks.append(xlat)
        for bonus in level.bonuses:
            blocks.append(render_bonus(bonus))

    return "\n\n".join(blocks) + "\n"
