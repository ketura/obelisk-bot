# SpellRankDef

Per-mastery-level data for a `SpellDef`. Always 4 rows per spell —
levels 1=no skill, 2=basic, 3=advanced, 4=expert. Each row is
self-contained: it carries the English defaults, the mechanical
fields, *and* the 15 non-English translations of every translatable
field. The old `SpellRankTranslationDef` sibling table was folded
back into this one — the three-translatable-field shape (name +
desc + bonus_description) didn't fit `EntryDef`'s generic
name+desc-only schema, so spell ranks get their own expanded shape.

The bot emits these inline on the parent `Data:Spell/<id>` page.
There are no individual `Data:SpellRank/…` pages.

## Schema

```mediawiki
{{#cargo_declare:_table=SpellRankDef
| spell_id = String                 <!-- joins SpellDef.id -->
| level = Integer                   <!-- 1..4 -->

| name_sid = String                 <!-- spell name SID (shared across ranks; duplicated per row for clean queries) -->

| description_sid = String
| description = Wikitext            <!-- resolved English -->

<!-- Level-up bonus + upgrade cost.
     Null on level 1; populated on levels 2/3/4. -->
| bonus_description_sid = String
| bonus_description = Wikitext      <!-- resolved English -->

| mana_cost = Integer
| upgrade_cost = Integer

<!-- Per-language triples for every supported non-English locale.
     Each language gets a name + desc + bonus_description column. -->
| pt_br_name = String
| pt_br_desc = Wikitext
| pt_br_bonus_description = Wikitext
| cs_name = String
| cs_desc = Wikitext
| cs_bonus_description = Wikitext
| fr_name = String
| fr_desc = Wikitext
| fr_bonus_description = Wikitext
| de_name = String
| de_desc = Wikitext
| de_bonus_description = Wikitext
| hu_name = String
| hu_desc = Wikitext
| hu_bonus_description = Wikitext
| it_name = String
| it_desc = Wikitext
| it_bonus_description = Wikitext
| ja_name = String
| ja_desc = Wikitext
| ja_bonus_description = Wikitext
| ko_name = String
| ko_desc = Wikitext
| ko_bonus_description = Wikitext
| pl_name = String
| pl_desc = Wikitext
| pl_bonus_description = Wikitext
| ru_name = String
| ru_desc = Wikitext
| ru_bonus_description = Wikitext
| es_name = String
| es_desc = Wikitext
| es_bonus_description = Wikitext
| tr_name = String
| tr_desc = Wikitext
| tr_bonus_description = Wikitext
| uk_name = String
| uk_desc = Wikitext
| uk_bonus_description = Wikitext
| zh_cn_name = String
| zh_cn_desc = Wikitext
| zh_cn_bonus_description = Wikitext
| zh_tw_name = String
| zh_tw_desc = Wikitext
| zh_tw_bonus_description = Wikitext
}}
```

## Field notes

- **Primary key is `(spell_id, level)`.**
- **`name_sid`** carries the spell's name SID — same value across all
  four ranks for a given spell. Duplicated per-row so a query against
  `SpellRankDef` alone can render a labeled per-rank table without
  joining back to `SpellDef`.
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
- **`<lang>_*` columns** are sparse — a row only carries the
  translations for which the corresponding SID exists. If a spell
  has no bonus_description_sid at a given level, all 15
  `<lang>_bonus_description` columns are simply absent from the
  emitted invocation.
- **Resolver context** for the non-English lookups uses the same
  per-rank `magic_json = {"raw": spell.raw_json, "level": <level>}`
  context the English lookup uses, so per-mastery-level magicDealer
  values substitute identically across all 16 languages.

## Related tables

- [`SpellDef`](SpellDef.md) — joined on `spell_id = id` (N:1).

## Notes

- **`SpellRankTranslationDef` is gone.** The old shape (separate
  table with 45 lang columns + 3 SID columns) was redundant with the
  data already on `SpellRankDef`. Folding eliminated one Cargo table
  + cut the per-spell row count from 8 to 4 with no information loss.
