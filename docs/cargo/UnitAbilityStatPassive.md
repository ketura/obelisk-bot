# UnitAbilityStatPassive

Splinter for `ability_type = stat_passive`. Synthesized rows: the bot
spots stat-mechanic JSON blocks (e.g. `{"attackPen": 0.3}`) on a unit's
`data.stats`, recognizes the mechanic key from a registry, and creates a
UnitAbility row with the shared name/desc SIDs that other units with the
same stat passive use.

Examples: Godslayer's `outDamageIfLevelAbove: 0.5` → "Apex Predator".
Multiple units with `attackPen` → all share the "Unyielding" name + a
common `base_passive_<mechanic>_<rank>_*` SID family.

Join to `UnitAbility` on `ability_id`.

## Schema

```mediawiki
{{#cargo_declare:_table=UnitAbilityStatPassive
| ability_id = String                         <!-- FK -> UnitAbility.ability_id -->
| affected_stat = String                      <!-- mechanic key, e.g. "attackPen", "armorPen" -->
| affected_stat_amount = Float
}}
```

## Field notes

- **`affected_stat`** holds the source mechanic key from the unit JSON's
  `data.stats` block. It's the *raw* key (e.g. `outDamageIfLevelAbove`,
  not the human-readable "Apex Predator"). The display name lives on
  the parent `UnitAbility` row's `name` field, resolved from the shared
  `base_passive_*` SID.
- **`affected_stat_amount`** is the concrete value, e.g. `0.5` for a
  50% bonus. Wiki templates that render stat passives format it
  according to the mechanic — `attackPen` displays as a percent,
  `outDamageIfLevelAbove` as an absolute multiplier, etc.
- **The mapping mechanic-key → display-name + SID** is in
  `artificer.emit.unit`'s `STAT_PASSIVE_REGISTRY`. New mechanic keys
  surface in the audit report when the bot can't classify them.
- **No L10n fields here:** the parent UnitAbility row carries `name_sid`
  and `desc_sid` pointing at the shared `base_passive_*` SID family.
  The translation row picks those up the same way as any other ability.

## Related tables

- [`UnitAbility`](UnitAbility.md) — parent (1:1 on `ability_id`).

## Notes
