# ItemSetDef

A named curated group of artifacts that grant additional bonuses
when the hero equips multiple set pieces. 24 sets in the 2026-05-03
corpus, each containing 2-8 artifacts. Each set has 1-3 unlock
tiers, each tier requiring a different number of equipped pieces
to activate.

The "item set" terminology preserves source naming — both the source
JSON (`itemSet`, `itemsInSet`, `item_sets.json`) and players
colloquially call these "item sets" rather than "artifact sets".
The artifact entity itself was renamed to Artifact (per D-031),
but the set wrapper keeps the older terminology for searchability.

The bot emits each set at `Data:ItemSet/<id>` carrying:

1. `{{ItemSetDef | id=… | name=… | items_in_set=… | …}}` — main row.
2. `{{TranslationDef | type=item_set | target_id=<id> | …}}` — name
   translations (per D-026).
3. For each tier: a `{{ItemSetTierDef | id=… | required_amount=… | …}}`
   row, a `{{TranslationDef | type=item_set_tier | target_id=<tier_id>
   | <lang>_desc=… }}` row (desc-only, no name), and N
   `{{BonusDef | parent_type=item_set_tier | parent_id=<tier_id> | …}}`
   rows.

## Schema

```mediawiki
{{#cargo_declare:_table=ItemSetDef
| id = String
| name = String                  <!-- resolved English; translations on Translation rows -->
| name_sid = String
| items_in_set = List (,) of String  <!-- joins Artifact.id -->
| source_path = String
}}
```

## Field notes

- **`id`** is the source JSON id (e.g. `tranquility_item_set`,
  `beelzebubs_blessing_item_set`).
- **`items_in_set`** is the comma-joined list of artifact ids that
  belong to this set. Used by the wiki side to render a "set
  contents" panel; joined to `Artifact.id` per element.
- Set sizes range from 2 to 8 artifacts (median 3-4).
- **No description on the set itself** — descriptions are per-tier
  and live on `ItemSetTierDef`.

## Related tables

- [`ItemSetTierDef`](ItemSetTierDef.md) — joined on `id = set_id` (1:N,
  1-3 tiers per set).
- [`ArtifactDef`](ArtifactDef.md) — `items_in_set` references
  `Artifact.id`; `Artifact.artifact_set_id` is the inverse pointer.
- [`TranslationDef`](shared/Translation.md) — one row per set with
  `type=item_set` (name only).

## Notes
