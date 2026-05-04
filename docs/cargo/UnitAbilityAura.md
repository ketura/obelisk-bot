# UnitAbilityAura

Splinter for `ability_type = aura`. Range-1 unit-emanating effects.
Always one per unit in the current corpus (singular `aura` field on the
unit JSON). 6 instances in 2026-05-03: `angel`, `black_dragon_upg_alt`,
`ent_upg`, `esquire_upg_alt`, `fairy_dragon`, `qilin_upg_alt`.

Join to `UnitAbility` on `ability_id`.

## Schema

```mediawiki
{{#cargo_declare:_table=UnitAbilityAura
| ability_id = String                         <!-- FK -> UnitAbility.ability_id -->
| target = String (allowed values=ally,allynoself,enemy)
| power = Integer
| radius = Integer
| tag = String                                <!-- 6 distinct in the current corpus -->
| affected_stat = String
| affected_stat_amount = Float
}}
```

## Field notes

- **`target`** controls who the aura affects. `allynoself` excludes the
  emitting unit (e.g. Esquire's aura buffs only neighbors).
- **`power`** is currently always `1` in the corpus — the column is
  here as a future-proof. Higher values would mean multiple stacks of
  the aura's effect on each affected unit.
- **`radius`** is currently always `1` (adjacent hexes). Aura units are
  short-range battlefield-shapers.
- **`tag`** is the aura family name. Six distinct values in 2026-05-03:
  `angel_aura`, `black_dragon_aura`, `ent_aura`, `esquire_aura`,
  `fairy_dragon_aura`, `qilin_aura`.
- **`affected_stat` / `affected_stat_amount`** describe the stat the
  aura applies. May be missing for auras whose effect is a non-stat
  payload (currently fairy_dragon's `alwaysMinDmg: true` pattern would
  hit this — encoded as a bool, not a numeric stat, so the bot omits
  the `_amount` slot).

## Related tables

- [`UnitAbility`](UnitAbility.md) — parent (1:1 on `ability_id`).

## Notes
