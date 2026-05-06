# Spell

One row per spell. ~137 in the 2026-05-03 corpus across 5 schools
(day, night, primal, space, neutral) and 5 ranks. Includes battle
spells (cast in combat), world spells (cast on the adventure map),
and `_special` upgraded variants.

The bot emits each spell at `Data:Spell/<id>` carrying:

1. `{{Spell | id=… | name=… | school=… | rank=… | …}}` — main row
   with the split learn-cost columns inline.
2. 4 × `{{SpellRank | spell_id=<id> | level=<1-4> | …}}` paired with
   4 × `{{SpellRankTranslation | spell_id=<id> | level=<1-4> | …}}`
   — one pair per mastery level (1=no skill, 2=basic, 3=advanced,
   4=expert). Spells use the dedicated SpellRankTranslation table
   instead of the unified Translation (per D-030 revised) because
   the per-rank shape carries 3 localizable fields (name + desc +
   bonus_description) rather than the standard 2.

## Schema

```mediawiki
{{#cargo_declare:_table=Spell
| id = String
| name = String
| name_sid = String

| school = String (allowed values=day,night,primal,space,neutral)
| rank = Integer
| used_on_map = Boolean

| icon = String

| magic_type_description = String       <!-- SID for the type label, e.g. magic_type_healing -->

<!-- Special-magic flags -->
| is_special_magic = Boolean
| is_unique_magic = Boolean
| normal_magic_sid = String             <!-- back-ref for is_special_magic spells -->

<!-- Learn-cost split per resource. Sparse: zero/missing → omitted.
     Most spells use gemstones/crystals/mercury (94 spells); a small
     set of unique magics use star_dust (6 spells). -->
| learn_cost_gemstones = Integer
| learn_cost_crystals = Integer
| learn_cost_mercury = Integer
| learn_cost_star_dust = Integer

<!-- Misc sparse fields -->
| excaption_in_tooltip_sid = String     <!-- e.g. immunity callouts (note source typo "excaption") -->
| up_effect_description_sid = String
| use_expand_tooltip = Boolean
| energy_cost = Integer
| energy_type = String

| source_path = String
}}
```

## Field notes

- **`id`** is the source JSON id (e.g. `day_1_magic_healing_water`,
  `day_1_magic_healing_water_special`).
- **`school`** is one of 5: `day`, `night`, `primal`, `space`, `neutral`.
- **`rank`** is 1-5; the spell's intrinsic difficulty/tier.
- **`used_on_map`** distinguishes battle vs world spells.
  `worldMagic` and `battleMagic` sub-trees are not extracted as
  Cargo columns yet — they describe the in-game effect mechanics in
  detail; future work if a wiki need surfaces.
- **Special magics** (`is_special_magic=true`) point back at the
  base spell via `normal_magic_sid`. These are upgraded variants
  unlocked by certain heroes' specializations.
- **`excaption_in_tooltip_sid`** — source field name preserves the
  typo (`excaption` instead of `exception`); it points at SIDs like
  `description_effect_undead_embodiment_construct_immunities`
  ("Does not affect Undead, Embodiments, or Constructs"). The bot
  passes the source name through unchanged.
- **No `desc_sid` here.** Spell descriptions vary by mastery level
  and live on the SpellRank rows.

## Related tables

- [`SpellRank`](SpellRank.md) — joined on `id = spell_id` (1:N, 4
  rows per spell).
- [`SpellRankTranslation`](SpellRankTranslation.md) — joined on
  `id = spell_id` (1:N, 4 rows per spell). Carries the i18n payload
  for spell name + per-rank desc + per-rank bonus_description.
- `Hero.start_magics` — references spell ids via the comma-joined
  list column.

## Notes
