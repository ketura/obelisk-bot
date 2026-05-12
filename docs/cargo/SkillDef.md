# SkillDef

One row per hero skill. 102 rows total in 2026-05-05: 30 production + 12 pseudo + 30 arena + 30 campaign. Skills are the top-level branches of the hero skill tree (e.g. `skill_assault`, `skill_archery`, `skill_logistics`); each has 1-3 mastery levels, and at each level the player gets to pick from a small pool of sub-skills ("perks") that further specialize the build.

A skill carries identity (id, variant, type), shared name + desc SIDs, and a count of mastery levels. Per-level data (overrides, offered sub-skills, bonuses) lives on [`SkillLevelDef`](SkillLevelDef.md). The sub-skills available from a skill live on [`SubSkillDef`](SubSkillDef.md), recovered by scanning every level's `offered_sub_skills` list.

## Page layout

`Data:Skill/<id>` is self-contained — it carries the skill's own row plus every sub-skill referenced by any of its levels:

1. `{{SkillDef | id=… | variant=… | skill_type=… | …}}`
2. `{{TranslationDef | type=skill | target_id=<id> | …}}` — name + desc shared across all levels
3. N × `{{SkillLevelDef | skill_id=<id> | level=N | …}}`
4. N × `{{SkillLevelTranslationDef | skill_id=<id> | level=N | … }}` — only when level overrides a name/desc
5. M × `{{BonusDef | parent_type=skill_level | parent_id=<id>_L<level> | … }}`
6. K × `{{SubSkillDef | id=… | parent_skill_id=<id> | …}}` — every sub-skill referenced by any level
7. K × `{{TranslationDef | type=sub_skill | target_id=<sub_skill_id> | …}}`
8. K' × `{{BonusDef | parent_type=sub_skill | parent_id=<sub_skill_id> | …}}`

The 77 sub-skills not referenced by any skill (8 test entries + ~69 arena legacy `*_old` entries) emit onto the catch-all page `Data:Skill/_orphan_sub_skills` instead.

## Schema

```mediawiki
{{#cargo_declare:_table=SkillDef
| id = String
| variant = String              <!-- production / arena / campaign / pseudo -->
| skill_type = String           <!-- Common / Class / Faction; null for pseudo skills -->
| is_pseudo = Boolean
| name = String                 <!-- resolved English -->
| name_sid = String
| desc = Wikitext               <!-- resolved English; nullable -->
| desc_sid = String             <!-- nullable -->
| max_level = Integer           <!-- 1-3, == count(SkillLevel rows) -->
| source_path = String
}}
```

## Field notes

- **`id`** is the source JSON id (e.g. `skill_assault`, `arena_skill_assault`, `campaign_skill_assault`, `skill_pseudo_1`).
- **`variant`** distinguishes production / arena / campaign / pseudo variants of the same skill family. Most analytical queries should `WHERE variant = 'production'`.
- **`skill_type`** is one of `Common` / `Class` / `FactionDef`. Pseudo skills (the 12 `skill_pseudo_*` entries) carry no skill_type — they're internal mechanism skills not shown in the hero UI.
- **`is_pseudo`** mirrors the source `isPseudoSkill` flag. Pseudo skills typically have just 1 level and are used as reusable mechanic containers (e.g. movement bonuses applied uniformly).
- **`name_sid` / `desc_sid`** point at the L10n entries; `name` / `desc` are the resolved English mirrors for at-a-glance reading.
- **`max_level`** equals the length of the source `parametersPerLevel` array.

## Related tables

- [`SkillLevelDef`](SkillLevelDef.md) — joined on `id = skill_id` (1:N where N=1..3).
- [`SubSkillDef`](SubSkillDef.md) — joined on `id = parent_skill_id`. Recovered by scanning every level's `offered_sub_skills`.
- [`BonusDef`](shared/Bonus.md) — skill-level bonuses join on `parent_type='skill_level' AND parent_id LIKE id || '_L%'`.
- [`TranslationDef`](shared/Translation.md) — one row per skill with `type=skill`, `target_id=id`.
