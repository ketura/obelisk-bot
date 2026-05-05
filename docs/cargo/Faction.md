# Faction

One row per faction (6 rows total: `human`, `undead`, `dungeon`,
`nature`, `demon`, `unfrozen`). Carries the structural data the
in-game faction record holds — display name, description, biome,
signature resource, asset references — plus the SIDs the
`FactionTranslation` sibling joins on.

The bot emits one `{{Faction | …}}` template invocation at the top of
each `Data:Faction/<id>` page, immediately followed by the
`{{FactionTranslation | …}}` row for the 15 non-English locales.
City-name pool entries are *not* on this page — they emit separately
as `Entry` rows of `type=FactionCityName` (one row per city, see
[`shared/Entry.md`](shared/Entry.md) and D-025).

Faction laws (the `fractionLawsLines` skill-tree structure in source
JSON) are deferred — that ships when the dedicated FactionLaw work
lands. Until then the law tree shape is not surfaced on the wiki.

## Schema

```mediawiki
{{#cargo_declare:_table=Faction
| id = String (allowed values=human,undead,dungeon,nature,demon,unfrozen)
| name = String
| desc = Wikitext

| icon = String
| icon_faction_laws = String

| biome = String
| resource = String

| name_sid = String
| desc_sid = String

| source_path = String
}}
```

## Field notes

- **`id`** is the primary key. Six fixed values; `neutral` is *not* a
  faction here even though `Faction` enum includes it for unit
  classification — there's no `7_neutral.json` source file.
- **`name` / `desc`** carry the resolved English defaults inline.
  Translations live on `FactionTranslation` keyed by `name_sid` /
  `desc_sid`. Per HoMM tradition the faction's display name is the
  town-style name: "Temple", "Necropolis", "Dungeon", "Grove", "Hive",
  "Schism".
- **`icon`** is the asset filename for the standard faction crest
  (e.g. `fraction_human`); the source JSON's misspelling is
  preserved here since it's an asset path, not a normalized concept.
- **`icon_faction_laws`** is a separate icon used on the faction-laws
  panel (e.g. `Scroll_Faction_Human`). Renamed from JSON's
  `iconFractionLaws`.
- **`biome`** is the faction's signature terrain (`Grass`, `Deathland`,
  `Dirt`, `Autumn`, `Lava`, `Snow`). One per faction, all distinct in
  the 2026-05-03 corpus.
- **`resource`** is the faction's signature resource (`gemstones`,
  `mercury`, `crystals`). Renamed from JSON's `resourceName`.
  Distribution: gemstones (human, dungeon), mercury (undead,
  unfrozen), crystals (nature, demon).
- **`source_path`** is the JSON path relative to `Core/`, useful for
  audit / diff traceability.

## Dropped from source

The source JSON's `narrativeDesc` field references SIDs of the form
`<id>_narrative_desc` that exist in *no* language file in the
2026-05-03 corpus. Dead pointer; we drop the field entirely. If a
future patch populates the SIDs, we'll add the column back.

## Related tables

- [`FactionTranslation`](FactionTranslation.md) — joined on `id =
  faction_id` (1:1) for the 15 non-English locales.
- [`Entry`](shared/Entry.md) where `type='FactionCityName'` — joined
  via `subtype LIKE '<faction>_%'` to surface this faction's
  randomization-pool city names.
- [`Unit`](Unit.md) — joined via `Unit.faction = Faction.id` (1:N).

## Notes
