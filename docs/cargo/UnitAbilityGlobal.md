# UnitAbilityGlobal

Splinter for `ability_type = global_passive`. Side-wide effects with no
radius — the whole side (allies or enemies) is affected as long as the
unit is on the battlefield. 11 instances in the 2026-05-03 corpus.

Join to `UnitAbility` on `ability_id`.

## Schema

```mediawiki
{{#cargo_declare:_table=UnitAbilityGlobal
| ability_id = String                         <!-- FK -> UnitAbility.ability_id -->
| target = String (allowed values=ally,enemy)
| power = Integer
| tag = String                                <!-- 5 distinct in the current corpus -->
| affected_stat = String
| affected_stat_amount = Float
}}
```

## Field notes

- **`target`** — which side this applies to. `ally` for unit-side
  buffs, `enemy` for unit-side debuffs (e.g. Olgoi's `enemy luck -1`
  aura). Note this column is named `target` here rather than the
  `global_target` it carries on the `UnitAbility` model — the splinter's
  context disambiguates the prefix.
- **`power`** scales with rank/upgrade level. Base unit might have
  `power=1`; the upg variant pushes the same effect to `power=2`.
- **`tag`** identifies the global-passive family. Distinct values in
  2026-05-03: `avatar_of_war_aura`, `black_dragon_ally_aura`,
  `black_dragon_enemy_aura`, `olgoi_aura`, `sunlight_cavalry_aura`. The
  tag is shared across variants of the same source unit, so it's a
  cheap way to find related rows.
- **`affected_stat` / `affected_stat_amount`** describe the stat the
  global passive applies. Always a single stat in the current corpus.

## Related tables

- [`UnitAbility`](UnitAbility.md) — parent (1:1 on `ability_id`).

## Notes
