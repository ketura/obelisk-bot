# ItemSetTier

One unlock tier of an `ItemSet`. The hero unlocks the tier's bonuses
when they have ``required_amount`` artifacts from the parent set
equipped. Sets have 1-3 tiers each (~37 tiers across the 24 sets in
the 2026-05-03 corpus).

The bot emits these inline on the parent `Data:ItemSet/<id>` page.
There are no individual `Data:ItemSetTier/…` pages.

## Schema

```mediawiki
{{#cargo_declare:_table=ItemSetTier
| id = String                        <!-- synthesized: <set_id>_tier_<ordinal> -->
| set_id = String                    <!-- joins ItemSet.id -->
| ordinal = Integer                  <!-- 0-based position in source bonuses[] -->
| required_amount = Integer          <!-- pieces equipped to unlock -->

| description_sid = String
| description = Wikitext             <!-- resolved English -->
}}
```

## Field notes

- **Primary key is `id`**. The synthesized form
  `<set_id>_tier_<ordinal>` lets `Bonus.parent_id` join cleanly
  via `parent_type='item_set_tier'`.
- **`set_id`** is the parent — duplicated here as a column so
  filtering by set doesn't require parsing the composite id.
- **`required_amount`** values seen in the 2026-05-03 corpus:
  2 (×17 tiers), 3 (×11), 4 (×7), 5 (×2), 6 (×2), 8 (×1).
- **`description`** carries the resolved English text inline.
  Translations live on a `{{Translation | type=item_set_tier |
  target_id=<id>}}` row (desc-only — tiers have no name).

## Related tables

- [`ItemSet`](ItemSet.md) — joined on `set_id = id` (N:1).
- [`Bonus`](shared/Bonus.md) — joined on `id = parent_id` (1:N) where
  `Bonus.parent_type = 'item_set_tier'`. Each tier has 1-6 bonus
  effects.
- [`Translation`](shared/Translation.md) — one row per tier with
  `type=item_set_tier` and the description SIDs for the 15
  non-English locales.

## Notes
