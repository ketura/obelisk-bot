# Unit

One row per extracted creature. Combat stats, resource costs, faction
metadata, and classification flags. The bot emits one `{{Unit | …}}`
template invocation per unit at the top of `Data:Unit/<id>`. The
template's job on the wiki side is to call `#cargo_store` with these
parameters.

## Schema

```mediawiki
{{#cargo_declare:_table=Unit
| id = String
| unused = Boolean
| faction = String (allowed values=human,undead,dungeon,nature,demon,unfrozen,neutral)
| tier = Integer
| source_path = String

<!-- Localization references -->
| name = String
| desc = Wikitext
| name_sid = String
| desc_sid = String
| base_sid = String                          <!-- this unit's base form, if it's an upgrade -->
| upgrade_sid = String                        <!-- the unit's upgrade target, if it has one -->

<!-- Stats block (mirrors UnitStats) -->
| hp = Integer
| offence = Integer
| defence = Integer
| damage_min = Integer
| damage_max = Integer
| initiative = Integer
| speed = Integer
| luck = Integer
| morale = Integer
| energy_per_cast = Integer
| energy_per_round = Integer
| energy_per_take_damage = Integer
| action_points = Integer
| num_counters = Integer
| morale_min = Integer
| morale_max = Integer
| luck_min = Integer
| luck_max = Integer
| move_type = String (allowed values=ground,fly,teleport,jump)

<!-- Classification -->
| creature_type = String (allowed values=living,undead,demon,magic_creature,embodiment,dragon,construct)
| immunities = List (,) of String
| disablers = List (,) of String
| shared_abilities = List (,) of String      <!-- name SIDs of base_*/<faction>_* passives -->
| native_biome = String
| ai_archetype = String
| tags = List (,) of String
| leave_corpse = Boolean

<!-- Resource costs (sparse — only the resources this unit needs are populated) -->
| gold_cost = Integer
| wood_cost = Integer
| ore_cost = Integer
| mercury_cost = Integer
| dust_cost = Integer
| crystal_cost = Integer
| gemstone_cost = Integer

<!-- Misc -->
| squad_value = Integer                       <!-- AI-side squad-power scoring -->
| exp_bonus = Integer
}}
```

## Field notes

- **`unused`** is sparse-emitted: only present (as `yes`) for the small
  set of deprecated units (units whose `name_sid` has no English entry).
  Filter most queries with `WHERE unused != "yes"`.
- **`base_sid` / `upgrade_sid`** form the variant chain: `crossbowman` →
  `crossbowman_upg` → `crossbowman_upg_alt`. Each tier gets its own row.
- **`shared_abilities`** lists name SIDs of the base/faction passives
  this unit has (e.g. `base_passive_melee_attack_name`). The actual
  passive text lives in shared tables (Phase 2). The bot ships these as
  references so the wiki display layer can render them by lookup
  instead of duplicating text on every unit page.
- **Resource cost columns are sparse.** Most units have only `gold_cost`;
  tier-7s cost gold + a special resource. The `dust_cost` column reflects
  Olden Era's "dust" resource (analogous to mercury in HoMM3).
- **`creature_type` is derived** from data-immunities tagged
  `<class>_immunities` — `living_immunities` → `living`, etc. The unit's
  actual immunity tags live in `immunities`.
- **`name_sid` / `desc_sid`** are the join keys to `UnitTranslation`.

## Related tables

- [`UnitTranslation`](UnitTranslation.md) — joined on `name_sid` (1:1).
- [`UnitAbility`](UnitAbility.md) and its splinters — joined on
  `unit_id = id` (1:N).

## Wiki template notes

Stub for the wiki-side `Template:Unit`:

```mediawiki
<noinclude>
Wraps a single unit row in #cargo_store. Receives every Unit field as a
named parameter; sparse-rendered (i.e. unset params are just absent).
</noinclude><includeonly>{{#cargo_store:_table=Unit
| id={{{id|}}}
| unused={{{unused|}}}
| faction={{{faction|}}}
…
}}</includeonly>
```

## Notes
