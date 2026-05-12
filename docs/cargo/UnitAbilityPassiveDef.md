# UnitAbilityPassiveDef

Splinter for `ability_type = passive`. Most passives are pure-data
(immunities, disablers, stat overrides), already rolled up to the `UnitDef`
row. This table only holds scalars unique to the passive itself — which
in practice is just the rare `sequence_effect` flag.

Join to `UnitAbilityDef` on `ability_id`.

## Schema

```mediawiki
{{#cargo_declare:_table=UnitAbilityPassiveDef
| ability_id = String                         <!-- FK -> UnitAbility.ability_id -->
| sequence_effect = String (allowed values=add_attack_after_counter_melee,add_attack_after_counter_shoot,assist_ability,counter_before_attack)
}}
```

## Field notes

- **`sequence_effect`** marks passives that interact with the
  combat-action sequence. Only 14 / 327 passives in the 2026-05-03
  corpus have this set, so the table is mostly empty rows of just
  `ability_id`. That's intentional — the parent `UnitAbilityDef` row
  carries everything else (name, desc, sids).
- **Passives' classification data** (immunities, disablers, creature
  type) lives on the `UnitDef` row, not here. Those are properties of the
  unit, not a passive instance.
- **Action-triggered passives** (e.g. Hydra's regen-on-take-damage) have
  complex `actions[]` JSON the bot doesn't surface as columns. The wiki
  layer should treat `desc` as the source of truth for what they do.

## Related tables

- [`UnitAbilityDef`](UnitAbilityDef.md) — parent (1:1 on `ability_id`).

## Notes
