"""Per-skill wikitext page renderer.

Per D-037: each ``Data:Skill/<skill_id>`` page is self-contained —
it carries the top-level ``{{SkillDef}}`` row, all per-level
``{{SkillLevelDef}}`` + ``{{EntryDef | type=skill_level | …}}`` +
``{{BonusDef}}`` rows, and inlines every sub-skill referenced by any
of this skill's levels (``{{SubSkillDef}}`` + ``{{TranslationDef
type=sub_skill}}`` + ``{{BonusDef parent_type=sub_skill}}``).

The per-(skill, level) translation row used to be its own
``SkillLevelTranslationDef`` table; it now folds into the shared
``EntryDef`` via ``(type='skill_level', subtype=skill_id,
variant=level)``.

Orphan sub-skills (not referenced by any skill — the 8 test
sub-skills like ``sub_skill_marchOfWar`` plus a handful of arena
``*_old`` legacy entries) are emitted onto a single catch-all page
``Data:Skill/_orphan_sub_skills``.
"""

from __future__ import annotations

from typing import Any, Iterable

from obelisk.emit.cargo import render_call
from obelisk.emit.hero import render_bonus
from obelisk.emit.unit import render_translation_block
from obelisk.models.localization import LocalizationCorpus
from obelisk.models.skill import SkillLevelRecord, SkillRecord, SubSkillRecord
from obelisk.resolve import PlaceholderResolver


_SKILL_FIELD_ORDER: tuple[str, ...] = (
    "id", "variant", "skill_type", "is_pseudo",
    "name_sid",
    "desc_sid",
    "max_level",
    "source_path",
)

_SKILL_LEVEL_FIELD_ORDER: tuple[str, ...] = (
    "skill_id", "level",
    "name_sid",
    "desc_sid",
    "icon",
    "offered_sub_skills",
)

_SUB_SKILL_FIELD_ORDER: tuple[str, ...] = (
    "id", "variant", "parent_skill_id",
    "name_sid",
    "desc_sid",
    "icon",
    "source_path",
)


def _render_skill_main(
    skill: SkillRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> str:
    """Render the top-level {{Skill | …}} row.

    The shared ``desc_sid`` (e.g. ``skill_economy_desc``) carries
    ``{0}`` placeholders that resolve against per-level bonus
    parameters via ``CurrentSkillParameter``. Pick level 1's raw_json
    so the top-level row's ``desc`` shows level-1 numbers (the
    per-level descriptions on each {{SkillLevel}} row carry the right
    level-specific values).
    """
    params: dict[str, Any] = {
        "id": skill.id,
        "variant": skill.variant,
        "skill_type": skill.skill_type,
        "is_pseudo": skill.is_pseudo,
        "name_sid": skill.name_sid,
        "desc_sid": skill.desc_sid,
        "max_level": len(skill.levels),
        "source_path": skill.source_path,
    }
    return render_call("SkillDef", params, key_order=_SKILL_FIELD_ORDER)


def _render_skill_level(
    level: SkillLevelRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> str:
    params: dict[str, Any] = {
        "skill_id": level.skill_id,
        "level": level.level,
        "name_sid": level.name_sid,
        "desc_sid": level.desc_sid,
        "icon": level.icon,
        "offered_sub_skills": (
            ",".join(level.offered_sub_skills) if level.offered_sub_skills else None
        ),
    }
    return render_call("SkillLevelDef", params, key_order=_SKILL_LEVEL_FIELD_ORDER)


def _render_skill_level_translation(
    level: SkillLevelRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> str:
    """Per-(skill, level) Translation rows for a level's name/desc
    override, in every language (English included).

    Per D-040: emits ``{{TranslationDef | type='skill_level'}}`` rows
    keyed by ``target_id=<skill_id>`` + ``variant=<level>``. Sparse —
    returns the empty string when the level has neither a name nor a
    desc SID (the common case: most levels inherit the parent skill's
    display fields)."""
    if not level.name_sid and not level.desc_sid:
        return ""
    return render_translation_block(
        translation_type="skill_level",
        target_id=level.skill_id,
        name_sid=level.name_sid,
        desc_sid=level.desc_sid,
        corpus=corpus,
        variant=str(level.level),
        resolver=resolver,
        skill_json=level.raw_json,
        skill_level=level.level,
    )


def _render_sub_skill(
    sub: SubSkillRecord,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> tuple[str, str]:
    """Render one {{SubSkill}} row + its matching Translation row.

    Threads the sub-skill's raw JSON as ``sub_skill_json`` so the
    interpreter's ``CurrentSubSkill`` op can resolve per-bonus
    placeholders in the description."""
    params: dict[str, Any] = {
        "id": sub.id,
        "variant": sub.variant,
        "parent_skill_id": sub.parent_skill_id,
        "name_sid": sub.name_sid,
        "desc_sid": sub.desc_sid,
        "icon": sub.icon,
        "source_path": sub.source_path,
    }
    sub_block = render_call("SubSkillDef", params, key_order=_SUB_SKILL_FIELD_ORDER)
    xlat = render_translation_block(
        translation_type="sub_skill",
        target_id=sub.id,
        name_sid=sub.name_sid,
        desc_sid=sub.desc_sid,
        corpus=corpus,
        resolver=resolver,
        sub_skill_json=sub.raw_json,
    )
    return sub_block, xlat


def emit_skill_page(
    skill: SkillRecord,
    sub_skills: Iterable[SubSkillRecord],
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render ``Data:Skill/<skill_id>`` — top-level row + per-level
    rows + all sub-skills referenced from any of this skill's levels.

    ``sub_skills`` is the list of SubSkillRecord rows whose
    ``parent_skill_id`` equals ``skill.id``. Caller filters."""
    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        _render_skill_main(skill, corpus, resolver),
    ]

    # Top-level Translation row for the shared name/desc.
    # Thread first-level raw_json as skill_json so per-language descs
    # resolve their {0} placeholders against level-1 parameters
    # (parallels the top-level Skill row's en_desc choice).
    first_level_json = skill.levels[0].raw_json if skill.levels else None
    first_level = skill.levels[0].level if skill.levels else None
    xlat = render_translation_block(
        translation_type="skill",
        target_id=skill.id,
        name_sid=skill.name_sid,
        desc_sid=skill.desc_sid,
        corpus=corpus,
        resolver=resolver,
        skill_json=first_level_json,
        skill_level=first_level,
    )
    if xlat:
        blocks.append(xlat)

    # Per-level rows + per-level translation + per-level bonuses.
    for level in skill.levels:
        blocks.append(_render_skill_level(level, corpus, resolver))
        xlat_lv = _render_skill_level_translation(level, corpus, resolver)
        if xlat_lv:
            blocks.append(xlat_lv)
        for bonus in level.bonuses:
            blocks.append(render_bonus(bonus))

    # Inline the sub-skills attached to this skill, in declaration order.
    for sub in sub_skills:
        sub_block, sub_xlat = _render_sub_skill(sub, corpus, resolver)
        blocks.append(sub_block)
        if sub_xlat:
            blocks.append(sub_xlat)
        for bonus in sub.bonuses:
            blocks.append(render_bonus(bonus))

    return "\n\n".join(blocks) + "\n"


def emit_orphan_sub_skills_page(
    orphans: Iterable[SubSkillRecord],
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None = None,
) -> str:
    """Render the catch-all ``Data:Skill/_orphan_sub_skills`` page —
    SubSkill rows that aren't referenced by any skill (the 8 test
    sub-skills + a handful of arena ``*_old`` legacy entries)."""
    blocks: list[str] = [
        "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->",
        "<!-- Catch-all page for sub-skills not referenced by any "
        "skill's subSkills[] list (test entries + legacy arena variants). -->",
    ]
    for sub in orphans:
        sub_block, sub_xlat = _render_sub_skill(sub, corpus, resolver)
        blocks.append(sub_block)
        if sub_xlat:
            blocks.append(sub_xlat)
        for bonus in sub.bonuses:
            blocks.append(render_bonus(bonus))
    return "\n\n".join(blocks) + "\n"
