# UnitAbilityConditionalDef

Splinter for `ability_type = conditional_passive`. Encodes
"if condition is met, the unit gets stat bonus X." 17 instances in the
2026-05-03 corpus, mostly the demon-faction "if your army has N unique
demons" pattern.

Join to `UnitAbilityDef` on `ability_id`.

## Schema

```mediawiki
{{#cargo_declare:_table=UnitAbilityConditionalDef
| ability_id = String                         <!-- FK -> UnitAbility.ability_id -->
| condition_check = String                    <!-- e.g. "unique_units_count" -->
| condition_target = String                   <!-- e.g. "ally" -->
| condition_value = String                    <!-- e.g. "demon" -->
| affected_stat = String
| affected_stat_amount = Float
}}
```

## Field notes

- **`condition_*` fields decompose** the source JSON's positional triple
  `["unique_units_count", "ally", "demon"]` into three columns. This
  matches the structure of every conditional passive in the current
  corpus — the check function name, the side it applies to, and the
  parameter the check requires.
- **`condition_check` enum values** seen in the wild:
  - `unique_units_count` — "you have N or more units of a faction"
  - `unique_fractions_buff` — variant on the same theme
  - More may surface in future patches; treat as open-string.
- **`condition_target`:** typically `ally` or `enemy`.
- **`condition_value`:** a faction id (`demon`, `human`, …) or
  similar discriminator. Always a string.
- **`affected_stat` / `affected_stat_amount`** describe the bonus
  granted when the condition fires. The current corpus has at most one
  stat per conditional passive, so a single pair suffices. If a future
  patch adds multi-stat conditionals, this would become a list — handle
  by extending the splinter or moving to a side table.

## Related tables

- [`UnitAbilityDef`](UnitAbilityDef.md) — parent (1:1 on `ability_id`).

## Notes
