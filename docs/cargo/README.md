# Cargo schema reference

Each file in this directory is a `#cargo_declare` definition for one Cargo
table the bot writes to. They're meant to be pasted into a wiki page (one
table per page is the MediaWiki convention) when the wiki maintainers are
ready to provision Cargo storage.

## Tables

| Table | Purpose | Splinters of |
| --- | --- | --- |
| [`Unit`](Unit.md) | One row per unit. Combat stats, costs, classification. | — |
| [`UnitTranslation`](UnitTranslation.md) | One row per unit. Localized name/desc across the 15 non-English languages. | `Unit` (1:1) |
| [`UnitAbility`](UnitAbility.md) | One row per ability slot on each unit. Identity + L10n keys only. | — |
| [`UnitAbilityActive`](UnitAbilityActive.md) | The biggest splinter. All active-ability scalars (dealer, buff, target, shoot, …). | `UnitAbility` |
| [`UnitAbilityPassive`](UnitAbilityPassive.md) | Passive-only fields (currently just `sequence_effect`). | `UnitAbility` |
| [`UnitAbilityConditional`](UnitAbilityConditional.md) | Condition triple + stat bonus for `conditional_passive` rows. | `UnitAbility` |
| [`UnitAbilityGlobal`](UnitAbilityGlobal.md) | Side-wide passive (target, power, tag) for `global_passive` rows. | `UnitAbility` |
| [`UnitAbilityAura`](UnitAbilityAura.md) | Range-1 aura fields (target, power, radius, tag). | `UnitAbility` |
| [`UnitAbilityStatPassive`](UnitAbilityStatPassive.md) | Synthesized stat passive (e.g. attackPen → "Unyielding"). | `UnitAbility` |
| [`UnitAbilityTranslation`](UnitAbilityTranslation.md) | One row per ability. Localized name/desc across 15 non-English languages. | `UnitAbility` (1:1) |
| [`UnitAttack`](UnitAttack.md) | **One row per unit.** All four attack slots (default / counter / alt / alt2) collapse into a single wide row with slot-prefixed fields. References `AttackArchetype` via `<slot>_attack_type` and `AttackPassive` via `<slot>_passive`. | — |

## Shared reference tables

These tables live in [`shared/`](shared/) — they're hand-curated
reference data the wiki ships pre-populated, not extracted per patch.
Per-unit tables join into them by string id.

| Table | Purpose |
| --- | --- |
| [`shared/AttackArchetype`](shared/AttackArchetype.md) | Exactly 3 rows (melee, ranged, reach) carrying the canned attack-type description ("Melee Attack — Can only attack adjacent enemies. Provokes counterattacks."). |
| [`shared/AttackArchetypeTranslation`](shared/AttackArchetypeTranslation.md) | i18n sibling of `AttackArchetype` for the 15 non-English languages. |
| [`shared/AttackPassive`](shared/AttackPassive.md) | ~9 rows for the named pattern-passives (Sweeping Strike, Whirlwind Strike, Dragonbreath Strike, Cone Strike, Area Strike, with falloff variants). One row per (token, rank). |
| [`shared/AttackPassiveTranslation`](shared/AttackPassiveTranslation.md) | i18n sibling of `AttackPassive`. |

## Join key conventions

The bot synthesizes a deterministic `ability_id` for every UnitAbility
row, formatted as:

```
<unit_id>[_<ability_type>]_<ordinal>[_<variant>]
```

with `active` omitted from the ability-type slot and `base` omitted from
the variant slot. Examples:

```
crossbowman_1                   active ability, base
crossbowman_passive_1           passive
inquisitor_2_upg_alt            active, upg_alt variant
godslayer_stat_passive_1        synthesized stat passive
```

Splinter tables and the translation table all carry this same `ability_id`
so a single-column join reaches every related row. See `D-019` in
`docs/decisions.md` for rationale.

## Sentinels and defaults

A few columns use sentinel values that wiki templates need to handle:

- `cd = -1` → once per battle. `cd = 0` → no cooldown.
- `action_cost = 0` → ability does not end the unit's turn (default is 1).
- `buff_duration = -1` → infinite. `buff_duration = 999` → until end of battle.
- `shoot_range = -1` → melee-only. `shoot_range = 99` → "infinite" for the engine.
- `unused = yes` → deprecated content the bot ships rows for to keep diff
  visibility. Most queries should filter `WHERE unused != "yes"`. Default
  for an active unit is the column being absent (NULL); this saves a
  column-emit on the 147+ rows that aren't deprecated.

`UnitAttack` columns are **slot-prefixed** (`default_*`, `counter_*`,
`alt_*`, `alt2_*`). Each slot carries its own set of defaults. See
`UnitAttack.md` for the full table; the gist:

- `default_*` → 1.0× damage, triggers counter, no cooldown.
- `counter_*` → 1.0× damage, does *not* trigger counter, no cooldown.
- `alt_*` / `alt2_*` → 0.5× damage, no counter. `cd=0` is the default;
  Fighting Style alts emit `cd=-1` explicitly. Most ranged-unit melee
  fallbacks emit zero override columns.
