# HeroSpecialization

One row per hero specialization (126 in the 2026-05-03 corpus: 108
faction + 9 campaign + 5 tutorial + 4 test). Each spec is the unique
passive that distinguishes one hero mechanically — every Hero record
carries `specialization_id` pointing at one of these.

The specialization carries identity (name, desc, icon) plus a
list of structured `bonuses[]` effects that compose the spec's
mechanical impact. Bonuses are emitted as inline
`{{HeroSpecializationBonus}}` rows on the same wiki page.

## Page layout

`Data:HeroSpecialization/<id>` carries:

1. `{{HeroSpecialization | id=… | name=… | desc=… | icon=… | …}}`
2. `{{Translation | type=hero_specialization | target_id=<id> | …}}`
3. N × `{{HeroSpecializationBonus | spec_id=<id> | ordinal=N | …}}`
   (1367 total bonus rows across all 126 specs)

## Schema

```mediawiki
{{#cargo_declare:_table=HeroSpecialization
| id = String
| name = String
| desc = Wikitext
| name_sid = String
| desc_sid = String
| icon = String
| source_path = String
}}
```

## Field notes

- **`id`** is the source JSON id (e.g. `human_hero_1_specialization`,
  `campaign_hero_4_specialization`). The `_specialization` suffix is
  preserved.
- **`name_sid` / `desc_sid`** point at the L10n entries
  (e.g. `human_hero_1_spec_name` / `human_hero_1_spec_description`).
  Description text is heavy with `{0}`/`{1}` placeholders for stat
  values; the resolver substitutes via the standard pipeline before
  storing.
- **`name` / `desc`** carry the resolved English text inline.
  Translations live on the `{{Translation | type=hero_specialization}}`
  row.
- **No `hero_id` back-reference.** The Hero → HeroSpecialization
  direction is sufficient (forward join via `Hero.specialization_id =
  HeroSpecialization.id`). Reverse queries — "which hero has this
  spec" — work via the same join. Per D-028.

## Related tables

- [`Hero`](Hero.md) — joined on `id = Hero.specialization_id` (1:1
  in practice; the schema permits N:1 in case a future patch shares
  specs across heroes).
- [`HeroSpecializationBonus`](HeroSpecializationBonus.md) — joined
  on `id = spec_id` (1:N).
- [`Translation`](shared/Translation.md) — one row per spec with
  `type=hero_specialization`, `target_id=id`.

## Notes
