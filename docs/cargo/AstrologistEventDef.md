# AstrologistEventDef

One row per astrologist event — the periodically-rolled global modifiers the in-game Astrologer announces between weeks and months. 26 entries total in 2026-05-05: 15 weeks (e.g. "Week of Sorcery", "Week of Luck") + 11 months ("Month of the Locust", and so on).

A single discriminator column `category` separates weeks from months — the source ships them in two parallel files (`DB/weeks/weeks.json` + `DB/weeks/months.json`) but the schema is identical, so we collapse to one table.

## Page layout

`Data:AstrologistEvent/<id>` carries:

1. `{{AstrologistEventDef | id=… | category=week|month | name=… | desc=… | …}}`
2. `{{TranslationDef | type=astrologist_event | target_id=<id> | …}}` — name+desc in the 16 supported languages

## Schema

```mediawiki
{{#cargo_declare:_table=AstrologistEventDef
| id = String
| category = String              <!-- week | month -->
| name = String                  <!-- resolved English -->
| name_sid = String
| desc = Wikitext                <!-- resolved English -->
| desc_sid = String              <!-- nullable -->
| icon = String                  <!-- nullable -->
| buff_sid = String              <!-- nullable; pointer into DB/buffs/ for the actual mechanical effect -->
| roll_chance = Integer          <!-- nullable; weight in the random-pick table -->
| count_to_return = Integer      <!-- global re-roll threshold (countToReturnWeek / countToReturnMonth) -->
| source_path = String
}}
```

## Field notes

- **`id`** is the source JSON id (e.g. `astrologist_week_1`, `astrologist_month_3`).
- **`category`** is the primary filter discriminator: `WHERE category='week'` to find every week event.
- **`buff_sid`** points at an entry in `DB/buffs/` carrying the actual mechanical payload (the bonuses the buff applies while the event is active). Not flattened into this table — the player-facing description on the event already covers gameplay impact.
- **`roll_chance`** is the relative weight in the engine's random-pick table when an astrology phase rolls. Per-event scalar; values across the 15-week table sum to roughly the same magnitude as the 11-month table since each is independently rolled.
- **`count_to_return`** is the global re-roll cooldown — the same event can't repeat within this many ticks. Stored per row (rather than as a global config) so queries don't need a join. Currently 3 for weeks and (a different value, see `weeks_info.json`) for months.

## Related tables

- [`TranslationDef`](shared/Translation.md) — one row per event with `type=astrologist_event`, `target_id=id`.
