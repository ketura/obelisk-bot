# ArtifactDef

One row per artifact / equipment item. 304 rows in the 2026-05-03
corpus, across 13 source slot files (armor, head, ring, boots,
back, belt, right_hand, left_hand, item_slot, unic_slot,
magic_scroll, enchante_magic_scroll, mythic_scroll_box).

The source folder is `DB/items/items/` — using the JSON's "item"
spelling. The wiki side uses **artifact** per the in-game player-
facing label.

The bot emits each artifact at `Data:Artifact/<id>` carrying:

1. `{{ArtifactDef | id=… | name=… | description=… | slot=… | rarity=… | …}}`
   — main row with English defaults inline plus the SIDs for all
   four localizable fields (name, description, upgrade_description,
   narrative_description).
2. `{{TranslationDef | type=artifact | target_id=<id> | …}}` — name +
   description i18n (per D-026).
3. N × `{{BonusDef | parent_type=artifact | parent_id=<id> | …}}` — the
   artifact's bonuses, in the unified Bonus table (per D-031).

## Schema

```mediawiki
{{#cargo_declare:_table=ArtifactDef
| id = String
| name = String
| description = Wikitext
| name_sid = String
| description_sid = String
| upgrade_description_sid = String       <!-- shown when the artifact levels up -->
| upgrade_description = Wikitext
| narrative_description_sid = String     <!-- flavor text -->
| narrative_description = Wikitext
| icon = String

| slot = String                  <!-- armor, head, ring, item_slot, ... -->
| rarity = String (allowed values=common,rare,epic,legendary)
| artifact_set_id = String       <!-- joins ArtifactSet (when that table exists) -->

| goods_value = Integer          <!-- gold value when sold -->
| max_level = Integer            <!-- 1 = non-upgradable; higher = upgradable -->

<!-- Sparse: only present on artifacts that can level up -->
| cost_base = Integer            <!-- cost to upgrade from level 1 to 2 -->
| cost_per_level = Integer       <!-- additional cost per subsequent level -->

| reward_for_destroy = Integer   <!-- crystal/etc. reward when destroyed -->

| is_special_item = Boolean      <!-- magic scrolls and a few specials -->
| use_expand_tooltip = Boolean
| can_destroy = Boolean
| can_apply_bonus_always = Boolean

| source_path = String
}}
```

## Field notes

- **`slot`** is one of 10 distinct values. `item_slot` is the
  catch-all for non-equipment items (magic scrolls live here).
  `unic_slot` is for one-of-a-kind unique items. The values
  preserve the source's lowercase-snake spelling.
- **`rarity`** counts in the 2026-05-03 corpus: rare (114), common
  (101), epic (50), legendary (39).
- **`artifact_set_id`** is sparse — 83 of 304 artifacts belong to a
  set. Joins to a future `ArtifactSet` table (deferred per D-031).
  Renamed from source's `itemSet` for terminology consistency.
- **`max_level`** = 1 means the artifact doesn't upgrade. Artifacts
  with `max_level > 1` carry `cost_base` + `cost_per_level`
  populated.
- **`is_special_item`** is true for magic scrolls and a few special
  items — they typically use `bonuses[].type=heroMagicAddition` to
  add a spell to the hero's spellbook. The field name preserves the
  source's spelling rather than renaming to `is_special_artifact`
  (the source field is `isSpecialItem`).
- **`use_expand_tooltip`** in source ships as both bool and the
  string `"false"` on different artifacts; the bot normalizes to a
  proper bool.
- **No sub-fields for the `bonuses[]`** here — they emit as
  separate `BonusDef` rows. Query artifacts with their bonuses via
  `tables=Artifact, Bonus | join on=Artifact.id=Bonus.parent_id |
  where=Bonus.parent_type='artifact'`.

## Artifact sets — deferred

Source has 24 sets in `DB/items/item_sets/item_sets.json` with
nested `bonuses[].heroBonuses[]` structures (set-completion
thresholds + per-tier bonus lists). The schema needs a separate
design pass; tracked as future work. The future table will be
called `ArtifactSet` and `Artifact.artifact_set_id` will join to
its `id`.

## Related tables

- [`BonusDef`](shared/Bonus.md) — joined on `id = parent_id` (1:N).
- [`TranslationDef`](shared/Translation.md) — one row per artifact
  with `type=artifact`.
- `ArtifactSet` — *(future table; joined on `artifact_set_id = id`)*.

## Notes
