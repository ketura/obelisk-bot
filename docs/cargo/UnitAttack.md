# UnitAttack

**One row per unit.** All four attack slots — `default`, `counter`,
`alt`, `alt2` — collapse onto a single wide row, with each slot's
fields prefixed by the slot name. Pattern-passives like Sweeping
Strike / Whirlwind / Dragonbreath aren't duplicated on every page;
each slot references a shared [`AttackPassive`](shared/AttackPassive.md)
row by `attack_passive_id`.

This pivot from one-row-per-slot to one-row-per-unit landed because
(a) "list this unit's attacks" is the dominant query, and a single
fat row beats `GROUP BY unit_id` joins; (b) per-slot rows would
duplicate identity columns four ways for no benefit.

## Schema

```mediawiki
{{#cargo_declare:_table=UnitAttack
| unit_id = String                                          <!-- primary key -->

<!-- DEFAULT slot — what the unit does on a normal attack action. -->
| default_attack_type = String (allowed values=melee,ranged,reach)
| default_pattern_sid = String                              <!-- engine pattern; usually omitted (derivable from passive) -->
| default_passive = String                                  <!-- FK -> AttackPassive (or NULL) -->
| default_stat_dmg_mult = Float                             <!-- override; default 1.0 -->
| default_damage_target = String                            <!-- enemy | all | none ; default enemy -->
| default_affect_target = String                            <!-- enemy | noself | ally | … ; default enemy -->
| default_trigger_counter = Boolean                         <!-- default true -->
| default_damage_type = String                              <!-- normal | absolute | magic_pure ; default normal -->
| default_buff_sid = String                                 <!-- on-hit debuff slot -->
| default_buff_target = String
| default_buff_duration = Integer
| default_is_armed_ability = Boolean                        <!-- default false -->
| default_temp_self_buff = String
| default_dont_trigger_energy_regen = Boolean

<!-- COUNTER slot — what the unit does when retaliating. -->
| counter_attack_type = String (allowed values=melee,ranged,reach)
| counter_pattern_sid = String
| counter_passive = String
| counter_stat_dmg_mult = Float
| counter_damage_target = String
| counter_affect_target = String
| counter_trigger_counter = Boolean                         <!-- default false (counters don't counter the counter) -->
| counter_damage_type = String
| counter_buff_sid = String
| counter_buff_target = String
| counter_buff_duration = Integer
| counter_is_armed_ability = Boolean

<!-- ALT slot — situational fallback / Fighting Style / once-per-battle. -->
| alt_attack_type = String (allowed values=melee,ranged,reach)
| alt_pattern_sid = String
| alt_passive = String
| alt_stat_dmg_mult = Float                                 <!-- default 0.5 -->
| alt_damage_target = String
| alt_affect_target = String
| alt_trigger_counter = Boolean                             <!-- default false -->
| alt_damage_type = String
| alt_buff_sid = String
| alt_buff_target = String
| alt_buff_duration = Integer
| alt_cd = Integer                                          <!-- -1 = once per battle -->
| alt_dont_use_energy = Boolean
| alt_return_to_start_after_attack = Boolean
| alt_never_disable = Boolean
| alt_temp_self_buff = String
| alt_dont_trigger_energy_regen = Boolean
| alt_multitarget_type = String                             <!-- ordered | simultaneous -->
| alt_num_targets = Integer
| alt_is_armed_ability = Boolean

<!-- ALT2 slot — same shape as alt. Only Medusa and a handful use this. -->
| alt2_attack_type = String (allowed values=melee,ranged,reach)
| alt2_pattern_sid = String
| alt2_passive = String
| alt2_stat_dmg_mult = Float
| alt2_damage_target = String
| alt2_affect_target = String
| alt2_trigger_counter = Boolean
| alt2_damage_type = String
| alt2_buff_sid = String
| alt2_buff_target = String
| alt2_buff_duration = Integer
| alt2_cd = Integer
| alt2_dont_use_energy = Boolean
| alt2_return_to_start_after_attack = Boolean
| alt2_never_disable = Boolean
| alt2_temp_self_buff = String
| alt2_dont_trigger_energy_regen = Boolean
| alt2_multitarget_type = String
| alt2_num_targets = Integer
| alt2_is_armed_ability = Boolean
}}
```

## Field notes — slot conventions

- **`<slot>_attack_type`** is the only slot field that's always present
  when the slot itself is populated. If the unit has no slot of a
  given category, *all* `<slot>_*` columns are NULL/absent.
- **`<slot>_passive`** references [`AttackPassive`](shared/AttackPassive.md)
  by id. Most units leave this NULL (their attack pattern is plain
  `attack_single_x100` with no special passive). Patterns that
  resolve to a known passive get the id; unknown patterns fall back to
  a `pattern_passive_TODO_<pattern_sid>` placeholder so the gap is
  visible.
- **`<slot>_pattern_sid`** is usually omitted — the canonical pattern
  is implied by the passive_id. The bot only emits this when the
  unit's actual pattern differs from the passive's canonical sid (rare,
  e.g. `attack_reach_x2_x100_x100_x100_with_delay` is rank-2 of the
  Dragonbreath family; the bot stores the variant for forensic
  visibility).

## Field notes — defaults

The wiki template provides typed defaults; the bot omits any column
whose value matches the default. Slot-specific defaults:

| Field | `default_*` | `counter_*` | `alt_*` / `alt2_*` |
| --- | --- | --- | --- |
| `stat_dmg_mult` | `1.0` | `1.0` | `0.5` |
| `trigger_counter` | `true` | `false` | `false` |
| `damage_target` | `enemy` | `enemy` | `enemy` |
| `affect_target` | `enemy` | `enemy` | `enemy` |
| `damage_type` | `normal` | `normal` | `normal` |

Flat defaults (same regardless of slot):

- `is_armed_ability`, `dont_trigger_energy_regen`, `dont_use_energy`,
  `return_to_start_after_attack`, `never_disable` → `false`
- `cd` → `0` for default/counter, `-1` for `alt`/`alt2` is **not**
  the default (Crossbowman's plain melee fallback has cd=0). The
  template defaults `<alt>_cd` to `0`; Fighting Style alts emit
  `cd=-1` explicitly.
- `pattern_sid`, `passive`, `buff_*`, `temp_self_buff`,
  `multitarget_type`, `num_targets` → NULL

## Field notes — slot rarity

| Slot | Population rate | Notes |
| --- | --- | --- |
| `default_*` | ~99% of units | Almost everyone has a default attack |
| `counter_*` | ~99% of units | Almost everyone has a counter |
| `alt_*` | ~50% of units | Ranged units' melee fallback, Fighting Style alts |
| `alt2_*` | ~3% of units | Medusa-tier (melee fallback + Arrow Barrage) |

Wide schema, sparse data: the typical row emits ~5 lines (the slot
fields that deviate from defaults, plus identity columns).

## Sentinels

- `<alt>_cd = -1` → once per battle.
- `<slot>_buff_duration = -1` → infinite; `999` → until end of battle.

## Related tables

- [`AttackArchetype`](shared/AttackArchetype.md) — joined on
  `<slot>_attack_type` (3 rows; canned per-attack-type description).
- [`AttackPassive`](shared/AttackPassive.md) — joined on
  `<slot>_passive` (4 references per row).
- [`Unit`](Unit.md) — joined on `unit_id = id` (1:1).

## Wiki template notes

```mediawiki
<noinclude>
Wraps a unit's attack data in a single #cargo_store. Receives every
UnitAttack field as a named parameter; sparse-rendered with role-aware
defaults via {{{<slot>_<field>|default}}} backstops.
</noinclude><includeonly>{{#cargo_store:_table=UnitAttack
| unit_id={{{unit_id|}}}

| default_attack_type={{{default_attack_type|}}}
| default_pattern_sid={{{default_pattern_sid|}}}
| default_passive={{{default_passive|}}}
| default_stat_dmg_mult={{{default_stat_dmg_mult|1.0}}}
| default_damage_target={{{default_damage_target|enemy}}}
| default_affect_target={{{default_affect_target|enemy}}}
| default_trigger_counter={{{default_trigger_counter|true}}}
| default_damage_type={{{default_damage_type|normal}}}
| default_buff_sid={{{default_buff_sid|}}}
| default_buff_target={{{default_buff_target|}}}
| default_buff_duration={{{default_buff_duration|}}}
| default_is_armed_ability={{{default_is_armed_ability|false}}}
| default_temp_self_buff={{{default_temp_self_buff|}}}
| default_dont_trigger_energy_regen={{{default_dont_trigger_energy_regen|false}}}

| counter_attack_type={{{counter_attack_type|}}}
| counter_pattern_sid={{{counter_pattern_sid|}}}
| counter_passive={{{counter_passive|}}}
| counter_stat_dmg_mult={{{counter_stat_dmg_mult|1.0}}}
| counter_damage_target={{{counter_damage_target|enemy}}}
| counter_affect_target={{{counter_affect_target|enemy}}}
| counter_trigger_counter={{{counter_trigger_counter|false}}}
| counter_damage_type={{{counter_damage_type|normal}}}
| counter_buff_sid={{{counter_buff_sid|}}}
| counter_buff_target={{{counter_buff_target|}}}
| counter_buff_duration={{{counter_buff_duration|}}}
| counter_is_armed_ability={{{counter_is_armed_ability|false}}}

| alt_attack_type={{{alt_attack_type|}}}
| alt_pattern_sid={{{alt_pattern_sid|}}}
| alt_passive={{{alt_passive|}}}
| alt_stat_dmg_mult={{{alt_stat_dmg_mult|0.5}}}
| alt_damage_target={{{alt_damage_target|enemy}}}
| alt_affect_target={{{alt_affect_target|enemy}}}
| alt_trigger_counter={{{alt_trigger_counter|false}}}
| alt_damage_type={{{alt_damage_type|normal}}}
| alt_buff_sid={{{alt_buff_sid|}}}
| alt_buff_target={{{alt_buff_target|}}}
| alt_buff_duration={{{alt_buff_duration|}}}
| alt_cd={{{alt_cd|0}}}
| alt_dont_use_energy={{{alt_dont_use_energy|false}}}
| alt_return_to_start_after_attack={{{alt_return_to_start_after_attack|false}}}
| alt_never_disable={{{alt_never_disable|false}}}
| alt_temp_self_buff={{{alt_temp_self_buff|}}}
| alt_dont_trigger_energy_regen={{{alt_dont_trigger_energy_regen|false}}}
| alt_multitarget_type={{{alt_multitarget_type|}}}
| alt_num_targets={{{alt_num_targets|}}}
| alt_is_armed_ability={{{alt_is_armed_ability|false}}}

| alt2_attack_type={{{alt2_attack_type|}}}
| alt2_pattern_sid={{{alt2_pattern_sid|}}}
| alt2_passive={{{alt2_passive|}}}
| alt2_stat_dmg_mult={{{alt2_stat_dmg_mult|0.5}}}
| alt2_damage_target={{{alt2_damage_target|enemy}}}
| alt2_affect_target={{{alt2_affect_target|enemy}}}
| alt2_trigger_counter={{{alt2_trigger_counter|false}}}
| alt2_damage_type={{{alt2_damage_type|normal}}}
| alt2_buff_sid={{{alt2_buff_sid|}}}
| alt2_buff_target={{{alt2_buff_target|}}}
| alt2_buff_duration={{{alt2_buff_duration|}}}
| alt2_cd={{{alt2_cd|0}}}
| alt2_dont_use_energy={{{alt2_dont_use_energy|false}}}
| alt2_return_to_start_after_attack={{{alt2_return_to_start_after_attack|false}}}
| alt2_never_disable={{{alt2_never_disable|false}}}
| alt2_temp_self_buff={{{alt2_temp_self_buff|}}}
| alt2_dont_trigger_energy_regen={{{alt2_dont_trigger_energy_regen|false}}}
| alt2_multitarget_type={{{alt2_multitarget_type|}}}
| alt2_num_targets={{{alt2_num_targets|}}}
| alt2_is_armed_ability={{{alt2_is_armed_ability|false}}}
}}</includeonly>
```

## Notes
