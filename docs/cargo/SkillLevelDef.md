# SkillLevelDef

One row per (skill, level) pair. ~342 rows in 2026-05-05 across 102 skills. Most production / arena / campaign skills have 3 levels (Basic / Advanced / Expert mastery); pseudo skills typically have 1.

Each level carries optional name / desc / icon overrides (rare — most levels inherit the parent skill's display fields), the list of sub-skills that become offered at that level, and the bonuses that take effect when the player reaches that level. Per-level bonuses are emitted as `{{BonusDef | parent_type=skill_level | parent_id=<skill_id>_L<level> | …}}` rows.

## Schema

```mediawiki
{{#cargo_declare:_table=SkillLevelDef
| skill_id = String
| level = Integer                          <!-- 1-based; 1..max_level -->
| name = String                            <!-- resolved English; nullable -->
| name_sid = String                        <!-- nullable; per-level override only -->
| desc = Wikitext                          <!-- resolved English; nullable -->
| desc_sid = String                        <!-- nullable; per-level override only -->
| icon = String                            <!-- nullable; per-level override only -->
| offered_sub_skills = List (,) of String  <!-- sub-skill ids unlocked at this level -->
}}
```

## Field notes

- **Primary key is `(skill_id, level)`**.
- **`name_sid` / `desc_sid` / `icon`** are sparse — populated only when the level overrides the parent skill's defaults. Most levels leave these null and inherit from `Skill.name_sid` / `Skill.desc_sid`.
- **`offered_sub_skills`** is a Cargo `List (,) of String` — the sub-skill ids the player can pick from when reaching this level. `HOLDS`-friendly: `WHERE offered_sub_skills HOLDS 'sub_skill_offense'` to find every (skill, level) that offers a given perk. Empty for skills whose levels don't offer sub-skills (some pseudo skills, some campaign-only mechanics).
- **No `cost` column** — unlike Law levels, skill levels don't charge a separate spend; they're earned through the hero's general level-up mechanic.

## Related tables

- [`SkillDef`](SkillDef.md) — joined on `skill_id = Skill.id` (N:1).
- [`SubSkillDef`](SubSkillDef.md) — joined on `offered_sub_skills HOLDS SubSkill.id`.
- [`BonusDef`](shared/Bonus.md) — joined on `parent_type='skill_level' AND parent_id = skill_id || '_L' || level`.
- [`SkillLevelTranslationDef`](SkillLevelTranslationDef.md) — joined on `(skill_id, level)`. Carries per-level name/desc overrides in 16 languages, populated only when the level has its own `name_sid` / `desc_sid`.
