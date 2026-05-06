"""Per-law wikitext page renderer.

Per D-033: each ``Data:Law/<id>`` page carries a ``{{Law}}`` row,
a ``{{Translation | type=law | …}}`` row for the shared name, then
per-level: a ``{{LawLevel}}`` row, a ``{{LawLevelTranslation}}`` row,
and 0+ ``{{Bonus | parent_type=law_level | parent_id=<id>_L<level> | …}}``
rows.

Description SIDs are shared across levels but resolve to different
strings per level because each level's bonuses[].parameters values
are different — the resolver's ``CurrentFractionLawConfig`` op reads
from per-level law_json context.
"""

from __future__ import annotations

from typing import Any

from obelisk.emit.cargo import render_call
from obelisk.emit.hero import render_bonus
from obelisk.emit.unit import (
    LANG_CODE,
    _TRANSLATION_LANG_ORDER,
    _lookup_text,
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


def _law_level_translation_field_order() -> tuple[str, ...]:
    """Field order for {{LawLevelTranslation | …}}: (law_id, level,
    desc_sid) plus 15 non-English `<code>_desc` columns."""
    base = ("law_id", "level", "desc_sid")
    lang_cols = [
        f"{LANG_CODE[lang_dir]}_desc"
        for lang_dir in _TRANSLATION_LANG_ORDER
    ]
    return base + tuple(lang_cols)


_LAW_LEVEL_TRANSLATION_FIELD_ORDER: tuple[str, ...] = _law_level_translation_field_order()


def _render_level(
    law: LawRecord,
    level: LawLevelRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> str:
    """Render one {{LawLevel | …}} row. Builds a per-level law_json
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
    return render_call("LawLevel", params, key_order=_LAW_LEVEL_FIELD_ORDER)


def _render_level_translation(
    law: LawRecord,
    level: LawLevelRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> str:
    """Per-(law, level) translation row carrying the description in
    the 15 non-English locales. English description sits on
    LawLevel.description."""
    params: dict[str, Any] = {
        "law_id": law.id,
        "level": level.level,
        "desc_sid": law.desc_sid,
    }
    if law.desc_sid:
        for lang_dir in _TRANSLATION_LANG_ORDER:
            code = LANG_CODE[lang_dir]
            params[f"{code}_desc"] = _lookup_text(
                law.desc_sid, lang_dir, corpus, resolver, None, None,
                law_json=level.raw_json,
            )
    return render_call(
        "LawLevelTranslation",
        params,
        key_order=_LAW_LEVEL_TRANSLATION_FIELD_ORDER,
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
        render_call("Law", main_params, key_order=_LAW_FIELD_ORDER),
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

    # Per-level rows: structural + translation + N bonuses
    for level in law.levels:
        blocks.append(_render_level(law, level, corpus, resolver))
        blocks.append(_render_level_translation(law, level, corpus, resolver))
        for bonus in level.bonuses:
            blocks.append(render_bonus(bonus))

    return "\n\n".join(blocks) + "\n"
