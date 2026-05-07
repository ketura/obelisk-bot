"""Hero skill + sub-skill extraction.

Walks ``DB/heroes_skills/skills/*.json`` (4 files: prod / arena /
campaign / pseudo) and ``DB/heroes_skills/sub_skills/*.json`` (4
files: prod / arena / campaign / test).

Skills are flattened by ``parametersPerLevel`` into one
``SkillLevelRecord`` per (skill, level), mirroring the Building /
Law per-level pattern. Sub-skills are flat (no levels). The
sub-skill → parent-skill mapping is recovered by scanning every
skill level's ``subSkills[]`` list.

Per-level bonuses flow into the unified Bonus table with
``parent_type='skill_level'``; sub-skill bonuses use
``parent_type='sub_skill'``. See D-037.
"""

from __future__ import annotations

from typing import Any

from obelisk.extract.hero import build_bonus
from obelisk.extract.loader import CorePaths, iter_array, load_json
from obelisk.models.hero import Bonus
from obelisk.models.skill import (
    SkillExtractionResult,
    SkillLevelRecord,
    SkillRecord,
    SubSkillRecord,
)


# Skill-file name → variant tag.
_SKILL_FILE_VARIANTS: dict[str, str] = {
    "skills.json": "production",
    "skills_arena.json": "arena",
    "skills_campaign.json": "campaign",
    "pseudo_skills.json": "pseudo",
}

# Sub-skill file name → variant tag.
_SUB_SKILL_FILE_VARIANTS: dict[str, str] = {
    "sub_skills.json": "production",
    "sub_skills_arena.json": "arena",
    "sub_skills_campaign.json": "campaign",
    "sub_skills_test.json": "test",
}


def _build_skill_level(
    raw: dict[str, Any], *, skill_id: str, level: int,
) -> SkillLevelRecord:
    """Map one parametersPerLevel entry to SkillLevelRecord."""
    parent_id = f"{skill_id}_L{level}"
    bonuses: list[Bonus] = []
    for i, b in enumerate(raw.get("bonuses") or ()):
        if isinstance(b, dict):
            bonus = build_bonus(b, parent_type="skill_level",
                                parent_id=parent_id, ordinal=i)
            if bonus is not None:
                bonuses.append(bonus)
    offered = tuple(
        s for s in (raw.get("subSkills") or ()) if isinstance(s, str)
    )
    return SkillLevelRecord(
        skill_id=skill_id,
        level=level,
        name_sid=raw.get("name") if isinstance(raw.get("name"), str) else None,
        desc_sid=raw.get("desc") if isinstance(raw.get("desc"), str) else None,
        icon=raw.get("icon") if isinstance(raw.get("icon"), str) else None,
        offered_sub_skills=offered,
        bonuses=tuple(bonuses),
        raw_json=raw,
    )


def _build_skill(
    raw: dict[str, Any], *, variant: str, source_path: str,
) -> SkillRecord | None:
    skill_id = raw.get("id")
    if not isinstance(skill_id, str):
        return None
    levels: list[SkillLevelRecord] = []
    for i, level_raw in enumerate(raw.get("parametersPerLevel") or ()):
        if isinstance(level_raw, dict):
            levels.append(_build_skill_level(
                level_raw, skill_id=skill_id, level=i + 1,
            ))
    name_sid = raw.get("name")
    if not isinstance(name_sid, str):
        return None
    return SkillRecord(
        id=skill_id,
        variant=variant,
        skill_type=raw.get("skillType") if isinstance(raw.get("skillType"), str) else None,
        is_pseudo=bool(raw.get("isPseudoSkill", False)),
        name_sid=name_sid,
        desc_sid=raw.get("desc") if isinstance(raw.get("desc"), str) else None,
        levels=tuple(levels),
        source_path=source_path,
    )


def _build_sub_skill(
    raw: dict[str, Any],
    *,
    variant: str,
    source_path: str,
    parent_skill_id: str | None,
) -> SubSkillRecord | None:
    sub_id = raw.get("id")
    name_sid = raw.get("name")
    if not isinstance(sub_id, str) or not isinstance(name_sid, str):
        return None
    bonuses: list[Bonus] = []
    for i, b in enumerate(raw.get("bonuses") or ()):
        if isinstance(b, dict):
            bonus = build_bonus(b, parent_type="sub_skill",
                                parent_id=sub_id, ordinal=i)
            if bonus is not None:
                bonuses.append(bonus)
    return SubSkillRecord(
        id=sub_id,
        variant=variant,
        parent_skill_id=parent_skill_id,
        name_sid=name_sid,
        desc_sid=raw.get("desc") if isinstance(raw.get("desc"), str) else None,
        icon=raw.get("icon") if isinstance(raw.get("icon"), str) else None,
        bonuses=tuple(bonuses),
        source_path=source_path,
        raw_json=raw,
    )


def extract_skills(paths: CorePaths) -> SkillExtractionResult:
    """Walk DB/heroes_skills/{skills,sub_skills}/*.json. Returns all
    skill + sub-skill records, with sub-skill→parent-skill mapping
    recovered from each skill level's ``subSkills[]`` list."""
    skills_root = paths.db / "heroes_skills" / "skills"
    sub_root = paths.db / "heroes_skills" / "sub_skills"

    # First pass: load skills and build the (sub_skill_id -> parent_skill_id) map.
    skills: list[SkillRecord] = []
    parent_for_sub: dict[str, str] = {}
    if skills_root.is_dir():
        for fp in sorted(skills_root.glob("*.json")):
            variant = _SKILL_FILE_VARIANTS.get(fp.name, "production")
            rel = fp.relative_to(paths.core_root).as_posix()
            try:
                doc = load_json(fp)
            except Exception:
                continue
            for raw in iter_array(doc):
                if not isinstance(raw, dict):
                    continue
                skill = _build_skill(raw, variant=variant, source_path=rel)
                if skill is None:
                    continue
                skills.append(skill)
                for level in skill.levels:
                    for sub in level.offered_sub_skills:
                        # First skill that lists a given sub-skill wins
                        # (in practice, no overlap across the prod/arena/
                        # campaign variants since their ids are prefixed).
                        parent_for_sub.setdefault(sub, skill.id)

    # Second pass: load sub-skills, attaching parent_skill_id when known.
    sub_skills: list[SubSkillRecord] = []
    if sub_root.is_dir():
        for fp in sorted(sub_root.glob("*.json")):
            variant = _SUB_SKILL_FILE_VARIANTS.get(fp.name, "production")
            rel = fp.relative_to(paths.core_root).as_posix()
            try:
                doc = load_json(fp)
            except Exception:
                continue
            for raw in iter_array(doc):
                if not isinstance(raw, dict):
                    continue
                sub_id = raw.get("id")
                parent = parent_for_sub.get(sub_id) if isinstance(sub_id, str) else None
                rec = _build_sub_skill(
                    raw, variant=variant, source_path=rel,
                    parent_skill_id=parent,
                )
                if rec is not None:
                    sub_skills.append(rec)

    skills.sort(key=lambda s: (s.variant, s.id))
    sub_skills.sort(key=lambda s: (s.variant, s.id))
    return SkillExtractionResult(
        skills=tuple(skills),
        sub_skills=tuple(sub_skills),
    )
