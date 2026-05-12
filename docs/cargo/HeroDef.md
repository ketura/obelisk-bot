# HeroDef

One row per hero (~177 in the 2026-05-03 corpus: 108 faction + 46
campaign + 21 tutorial + 2 custom-map). Carries the per-hero
identity (name/motto/desc), the link to the parent
[`HeroClassDef`](HeroClassDef.md), and any class-default fields the hero
diverges on. Faction heroes match their class template exactly, so
their override fields are sparse-emitted (absent); campaign and
tutorial heroes routinely override `stats`, `start_level`, and
`attacks_times_before`.

The bot emits these per-hero blocks at `Data:Hero/<id>`:

1. `{{HeroDef | id=… | name=… | motto=… | desc=… | start_skills=… | start_magics=… | …}}`
   — main row. `start_skills` and `start_magics` are comma-joined SID
   lists inline on this row (no side tables for them).
2. `{{TranslationDef | type=hero | target_id=<id> | …}}` —
   name/desc translation (per D-026).
3. `{{TranslationDef | type=hero_motto | target_id=<id> | …}}` —
   motto translation (separate row, kept off the schema-specialization
   path; per D-027).
4. `{{HeroStartSquadDef | …}}` × N — one per starting squad slot (primary
   + alt collapsed via `variant` discriminator).

## Schema

```mediawiki
{{#cargo_declare:_table=HeroDef
| id = String
| name = String
| motto = Wikitext
| desc = Wikitext
| name_sid = String
| motto_sid = String
| desc_sid = String

| class_id = String              <!-- joins HeroClass.id (e.g. magic_demon) -->
| faction = String               <!-- denormalized from class -->
| class_type = String (allowed values=might,magic)

| icon = String
| specialization_id = String     <!-- joins HeroSpecialization.id -->

| source_path = String

<!-- Inline list-of-SID columns (always present; empty when none).
     start_skills and start_skill_levels are positionally aligned —
     the Nth element of start_skill_levels is the level for the Nth
     skill SID in start_skills. -->
| start_skills = List (,) of String        <!-- joins future Skill.id -->
| start_skill_levels = List (,) of Integer <!-- positionally aligned with start_skills -->
| start_magics = List (,) of String        <!-- joins future Spell.id -->

<!-- Note: spell level / isLearned are dropped (constant in the
     2026-05-03 corpus per D-027 revised). Skill level is preserved
     because 8/208 entries diverge from the default of 1. -->


<!-- Class-default override fields. Sparse: absent means inherit from
     HeroClass. Faction heroes always inherit (no overrides).
     Campaign/tutorial heroes routinely override stats + a few others. -->
| cost_gold = Integer
| start_level = Integer
| attacks_times_before = String      <!-- comma-joined floats -->
| mesh = String
| mount = String
| native_biome = String
| skills_roll_variant = String

<!-- Stat block overrides -->
| view_radius = Integer
| stats_num = Integer
| magic_casts_per_round = Integer
| enable_tactics = Boolean
| tactics_placement_size = Integer
| enable_hero_native_biome = Boolean
| offence = Integer
| defence = Integer
| spell_power = Integer
| intelligence = Integer
| luck = Integer
| morale = Integer

<!-- statsRolls overrides (named after the four primary stats; see
     HeroClass.md for the v=0..3 → attack/defense/power/knowledge
     mapping). -->
| roll_lvl1_attack = Integer
| roll_lvl1_defense = Integer
| roll_lvl1_power = Integer
| roll_lvl1_knowledge = Integer
| roll_lvl24_attack = Integer
| roll_lvl24_defense = Integer
| roll_lvl24_power = Integer
| roll_lvl24_knowledge = Integer
}}
```

## Override semantics

Every Cargo query that wants the effective value of a class-shared
field on a hero should use:

```sql
COALESCE(Hero.<col>, HeroClass.<col>) AS effective_<col>
```

Joining on `Hero.class_id = HeroClass.id`. Hero wins if present;
HeroClass fills in otherwise.

For faction heroes (108): all 11 class-shared columns are absent on
the Hero row — every query falls through to HeroClass.

For campaign/tutorial heroes: ~3-5 columns are typically present
(empirically: `stats_*`, `start_level`, `attacks_times_before`).
Other class-shared columns still inherit from HeroClass.

## Field notes

- **`id`** is the hero's source JSON id (e.g. `human_hero_1`,
  `campaign_M10_hero_demon_1`).
- **`name_sid`/`motto_sid`/`desc_sid`** carry the source SID for
  traceability and as the join key to the Translation rows.
  Faction heroes use implicit conventions
  (`<id>` / `<id>_motto` / `<id>_description`); campaign heroes set
  them explicitly in source JSON.
- **`name`/`motto`/`desc`** carry the resolved English text inline.
  Translations live on the two `TranslationDef` rows (one for name+desc,
  one for motto).
- **`class_id`** is `<class_type>_<faction>` — matches
  `HeroClass.id`.
- **`faction`/`class_type`** are denormalized from the class so
  that "all human heroes" / "all might heroes" filters don't need a
  join.
- **`specialization_id`** points at a row in `HeroSpecializationDef`
  (one specialization per hero, 1:1 ratio). Schema for that table
  comes in a follow-up.

## Related tables

- [`HeroClassDef`](HeroClassDef.md) — joined on `class_id = id` (N:1).
  Carries the class defaults the Hero row may override.
- [`HeroStartSquadDef`](HeroStartSquadDef.md) — joined on `hero_id = id`
  (1:N). Each row is one slot in primary or alt starting army.
- `SkillDef` (future) — joined on `start_skills` LIKE `%<sid>%` or via
  Cargo's `HOLDS` operator on the List column.
- `SpellDef` (future) — same join pattern via `start_magics`.
- [`HeroSpecializationDef`](HeroSpecializationDef.md) — joined on
  `specialization_id = id` (N:1). The hero's unique passive.
  *(Schema lands in a follow-up.)*
- [`TranslationDef`](shared/Translation.md) — two rows per hero
  (`type=hero` and `type=hero_motto`).

## Notes
