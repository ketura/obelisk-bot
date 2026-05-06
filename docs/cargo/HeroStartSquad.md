# HeroStartSquad

One row per slot in a hero's starting army. Each hero has 1-3
**primary** slots (`variant=primary`) and 1 **alt** slot
(`variant=alt`). Across the 108 faction heroes in the 2026-05-03
corpus: 100 have 3 primary slots, 5 have 2, 3 have 1; all 108 have
exactly 1 alt slot.

The bot emits these rows on the parent `Data:Hero/<id>` page, after
the `{{Hero}}` and `{{Translation}}` blocks.

## Schema

```mediawiki
{{#cargo_declare:_table=HeroStartSquad
| hero_id = String                <!-- joins Hero.id -->
| variant = String (allowed values=primary,alt)
| slot = Integer                  <!-- 1-based position within the variant -->
| unit_sid = String               <!-- joins Unit.id -->
| min = Integer
| max = Integer
}}
```

## Field notes

- **Primary key is `(hero_id, variant, slot)`**.
- **`variant`** distinguishes the source's parallel arrays
  `startSquad` (primary) and `startSquadAlt` (alt). Source data has
  alt as always exactly 1 slot of the form `(unit_sid, min=1, max=1)`
  in the 2026-05-03 corpus, but the schema preserves min/max in case
  future patches diverge.
- **`unit_sid`** references a `Unit.id` (e.g. `esquire`,
  `crossbowman`, `griffin`).
- **`min`/`max`** define the random count range for that slot at
  battle start. Primary slots have meaningful ranges (e.g. 14-20
  esquires); alt slots are typically 1-1.

## Related tables

- [`Hero`](Hero.md) — joined on `hero_id = id` (N:1).
- [`Unit`](Unit.md) — joined on `unit_sid = id` (N:1).

## Notes
