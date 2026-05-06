# SpellRank

Per-mastery-level data for a `Spell`. Always 4 rows per spell —
levels 1=no skill, 2=basic, 3=advanced, 4=expert.

The bot emits these inline on the parent `Data:Spell/<id>` page.
There are no individual `Data:SpellRank/…` pages.

## Schema

```mediawiki
{{#cargo_declare:_table=SpellRank
| spell_id = String                 <!-- joins Spell.id -->
| level = Integer                   <!-- 1..4 -->

| description_sid = String
| description = Wikitext            <!-- resolved English -->

| mana_cost = Integer

<!-- Level-up bonus + upgrade cost.
     Null on level 1; populated on levels 2/3/4. -->
| bonus_description_sid = String
| bonus_description = Wikitext      <!-- resolved English -->
| upgrade_cost = Integer
}}
```

## Field notes

- **Primary key is `(spell_id, level)`.**
- **`description_sid`** points at the source `description[level-1]`
  SID. Levels 1 and 2 often share the same SID (the "no mastery"
  text and the "basic" text are typically identical).
- **`description`** carries the resolved English text. Static
  spell-config placeholders are pre-substituted (the bot threads the
  spell's JSON through the resolver). **Hero-dependent placeholders
  (`{N}` for spell-power-scaled values) intentionally stay
  unsubstituted** — the actual numbers depend on the casting hero, so
  the wiki display layer surfaces them generically. See D-030.
- **`bonus_description_sid` / `bonus_description`** are the
  unlock-bonus message shown when reaching this level (e.g.
  "Affects all friendly creatures."). Null for level 1 (the starting
  rank).
- **`upgrade_cost`** is the resource cost paid to upgrade *to* this
  level (in the spell's primary upgrade resource — usually a small
  number like 25). Null for level 1. For length-1 source
  `upgradeCost` arrays (mostly world-map utility spells), only
  level 2 gets a value.

## Related tables

- [`Spell`](Spell.md) — joined on `spell_id = id` (N:1).

## Notes
