# Difficulty

One row per game difficulty setting. 5 entries in 2026-05-05: Easy / Normal / Hard / Expert / Impossible. Each carries the balance inputs the engine actually uses: per-side starting-resource buckets and the global `neutral_power_multiplier` (the scalar applied to adventure-map encounter strength).

Two source-data quirks worth flagging up front:

- The source `nameSid` values (`EasyDifficultySid`, `NormalDifficultySid`, …) are *not* L10n entries — they don't resolve in any `Lang/<locale>/` file. We store them on the row for fidelity, but the canonical display name is the `id` itself.
- The source `descriptionSid` field carries literal English text ("This is an Easy difficulty setting."), not an L10n key. We store it as a plain `description` string column.

Because of those, this table doesn't carry a companion `{{Translation}}` row — the source data ships in English only.

## Page layout

`Data:Difficulty/<id>` carries a single `{{Difficulty}}` row.

## Schema

```mediawiki
{{#cargo_declare:_table=Difficulty
| id = String                      <!-- Easy / Normal / Hard / Expert / Impossible -->
| name_sid = String                <!-- nullable; not actually in L10n corpus -->
| description = Wikitext           <!-- literal English from source descriptionSid -->
| neutral_power_multiplier = Float <!-- 0.5 / 0.75 / 1.0 / 1.5 / 2.0 -->
| player_gold = Integer
| player_wood = Integer
| player_ore = Integer
| player_gemstones = Integer
| player_crystals = Integer
| player_mercury = Integer
| player_dust = Integer
| ai_gold = Integer
| ai_wood = Integer
| ai_ore = Integer
| ai_gemstones = Integer
| ai_crystals = Integer
| ai_mercury = Integer
| ai_dust = Integer
| source_path = String
}}
```

## Field notes

- **`id`** comes from the source `sid` field. Five fixed values; new difficulty tiers would be a balance change worth flagging.
- **`neutral_power_multiplier`** is the headline balance number. 1.0 is "Hard" (the canonical reference point); Easy halves encounter strength, Impossible doubles it.
- **Resource columns**: source-side `alchemicalDust` is normalized to `dust` to match the canonical naming in [`Resource`](shared/Entry.md) (per `DB/res/resources_info.json`).
- **Asymmetry**: on Easy, the player starts with 3× the resources the AI does; this flips on Hard+, with the Impossible AI getting 5× the player's gold. That's the *primary* difficulty mechanism — `neutral_power_multiplier` only modulates map encounters.

## Related tables

- [`Resource`](shared/Entry.md) — the seven per-side `<player|ai>_<resource>` columns mirror the resource ids on the Resource Entry rows (gold / wood / ore / gemstones / crystals / mercury / dust).
