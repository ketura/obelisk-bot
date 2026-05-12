# SubSkillDef

Flat per-sub-skill ("perk") record. 617 rows in 2026-05-05: 203 production + 203 arena + 203 campaign + 8 test. Each sub-skill is a discrete pickable perk that the player chooses when their hero gains a skill mastery level — e.g. picking "Offense" vs "Defense" off the `skill_assault` Basic-mastery offering.

Sub-skills don't have levels of their own; they're flat. They carry identity (id, variant), display fields (name + desc + icon), the parent skill they were offered by (recovered from scanning every skill level's `offered_sub_skills` list), and the bonuses they grant. Bonuses flow into the unified [`BonusDef`](shared/Bonus.md) table with `parent_type='sub_skill'`.

## Page layout

Sub-skills are inlined on their parent skill's page (`Data:Skill/<parent_skill_id>`) — they share the page with the parent's `{{SkillDef}}`, `{{SkillLevelDef}}`, and per-skill `{{TranslationDef}}` rows. The 77 unreferenced sub-skills (8 test + ~69 arena legacy `*_old`) emit onto the catch-all page `Data:Skill/_orphan_sub_skills` with `parent_skill_id=NULL`.

Each sub-skill contributes:

1. `{{SubSkillDef | id=… | parent_skill_id=… | …}}`
2. `{{TranslationDef | type=sub_skill | target_id=<id> | …}}`
3. M × `{{BonusDef | parent_type=sub_skill | parent_id=<id> | … }}`

## Schema

```mediawiki
{{#cargo_declare:_table=SubSkillDef
| id = String
| variant = String              <!-- production / arena / campaign / test -->
| parent_skill_id = String      <!-- nullable; null for orphans -->
| name = String                 <!-- resolved English -->
| name_sid = String
| desc = Wikitext               <!-- resolved English; nullable -->
| desc_sid = String             <!-- nullable -->
| icon = String                 <!-- nullable -->
| source_path = String
}}
```

## Field notes

- **`id`** is the source JSON id (e.g. `sub_skill_offense`, `arena_sub_skill_offense_old`, `sub_skill_marchOfWar`).
- **`variant`** distinguishes production / arena / campaign / test variants. Most analytical queries should `WHERE variant = 'production'`.
- **`parent_skill_id`** is derived: the id of the [`SkillDef`](SkillDef.md) whose `{{SkillLevelDef}}` rows include this sub-skill in their `offered_sub_skills` list. NULL when no skill in the corpus references this sub-skill — those 77 orphans live on the `Data:Skill/_orphan_sub_skills` catch-all page (test entries + arena legacy `*_old`).
- **`name_sid` / `desc_sid`** point at the L10n entries; `name` / `desc` are the resolved English mirrors.

## Related tables

- [`SkillDef`](SkillDef.md) — joined on `parent_skill_id = Skill.id` (N:1).
- [`SkillLevelDef`](SkillLevelDef.md) — joined on `SkillLevel.offered_sub_skills HOLDS SubSkill.id` (N:M; a sub-skill is typically offered at exactly one (skill, level) but the relation is general).
- [`BonusDef`](shared/Bonus.md) — joined on `parent_type='sub_skill' AND parent_id = SubSkill.id`.
- [`TranslationDef`](shared/Translation.md) — one row per sub-skill with `type=sub_skill`, `target_id=id`.
