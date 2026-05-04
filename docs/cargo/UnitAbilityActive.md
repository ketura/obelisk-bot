# UnitAbilityActive

Splinter for `ability_type = active`. The biggest of the splinter
tables — every active ability has a dealer, target params, and
typically buff payload, plus optional damage tuning and shoot
parameters.

Join to `UnitAbility` on `ability_id`.

## Schema

```mediawiki
{{#cargo_declare:_table=UnitAbilityActive
| ability_id = String                         <!-- FK -> UnitAbility.ability_id -->

<!-- Active-row scalars (top-level keys on abilities[N] in the unit JSON) -->
| attack_type = String (allowed values=cast,end_move_attack,jump,melee,move,range,shoot)
| rank = Integer
| cd = Integer                                <!-- -1 = once per battle, 0 = no cooldown, N = N rounds -->
| energy_level = Integer
| action_cost = Integer                       <!-- defaults to 1; 0 = does not end the unit's turn -->
| charges = Integer
| disable_for_ai = Boolean
| never_disable = Boolean
| move_type_active = String (allowed values=teleport,walk)   <!-- distinct from Unit.move_type -->
| use_all_energy_levels = Boolean
| dont_use_energy = Boolean
| untargeted_cast = Boolean
| instacast = Boolean

<!-- damageDealer core fields -->
| attack_pattern_sid = String                 <!-- 17 distinct; future Data:AttackPattern reference -->
| damage_target = String (allowed values=all,enemy,none,noself)
| damage_type = String (allowed values=absolute,magic_pure,none,normal)
| stat_dmg_mult = Float                       <!-- 0.0 / 0.5 / 1.0 / 1.5 / 2.0 -->
| trigger_counter = Boolean
| multitarget_type = String (allowed values=ordered,simultaneous)
| num_targets = Integer
| dont_trigger_energy_regen = Boolean
| return_to_start_after_attack = Boolean

<!-- Direct damage tuning (rare; e.g. Bone Armageddon) -->
| min_base_dmg = Integer
| max_base_dmg = Integer
| min_stack_dmg = Integer
| max_stack_dmg = Integer
| min_damage_per_energy_level = Integer
| max_damage_per_energy_level = Integer
| damage_multipler_per_hero_level = Float
| temp_self_buff = String

<!-- Buff applied -->
| buff_sid = String                           <!-- 72+ distinct; future Data:Buff reference -->
| buff_target = String (allowed values=all,ally,allynoself,enemy,none,self)
| buff_duration = Integer                     <!-- -1 = infinite, 999 = until end of battle -->
| buff_charges = Integer

<!-- Ranged tuning (44 abilities, mostly arbitrator family) -->
| shoot_range = Integer                       <!-- -1 = melee-only, 99 = "infinite" -->
| shoot_threshold = Integer
| shoot_red_count = Integer
| shoot_dmg_buff = Float
| use_speed_as_shoot_range = Boolean

<!-- Cast target params (where the ability fires from) -->
| cast_target = String (allowed values=all,ally,allynoself,enemy,none,noself,self)
| cast_selection = String (allowed values=hex,hexOrObject,object)
| cast_target_condition = String (allowed values=alive,all,dead)
| cast_target_tags = List (,) of String

<!-- Affect target params (who the ability hits) -->
| affect_target = String (allowed values=all,ally,allynoself,enemy,noself,self)
| affect_selection = String (allowed values=hex,object)
| affect_target_condition = String (allowed values=alive,all,dead)
| affect_target_tags = List (,) of String
}}
```

## Field notes

- **`cd` sentinels:** `-1` = once per battle (one charge regenerates only
  through specific abilities); `0` = no cooldown; positive = rounds.
- **`action_cost`:** defaults to 1 (= consumes the unit's turn). `0`
  means the unit retains its action — wiki templates should display
  this as something like "free action" rather than rendering "0".
- **`stat_dmg_mult`** is a multiplier on basic-attack damage. `1.0` =
  standard damage, `0.5` = halved (e.g. ranged AoE), `2.0` = doubled.
  When the field is missing on the source JSON, the engine treats it
  as `1.0`.
- **`buff_*` fields** are sparse — only populated for abilities that
  apply a buff (~25% of active abilities). The buff's actual stats live
  in `DB/buffs/`, joined via `buff_sid`.
- **`shoot_*` fields** apply mostly to the arbitrator family
  (paradoxical-shot mechanic) and a handful of other ranged abilities.
- **`cast_target_tags` / `affect_target_tags`** are `List (,) of String`
  in Cargo — comma-separated in wiki, exposed as multi-row joins on
  Cargo's auxiliary `__values` table when queried.

## Related tables

- [`UnitAbility`](UnitAbility.md) — parent (1:1 on `ability_id`).
- Future `Buff` table — joined on `buff_sid`.
- Future `AttackPattern` table — joined on `attack_pattern_sid`.

## Notes
