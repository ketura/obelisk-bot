# AttackPassive

Shared reference table for **named attack-pattern passives** — the
side-effects-of-default-attack abilities that show up in unit tooltips
as passives (e.g. Hydra has "Sweeping Strike" inherent to its standard
melee attack). One row per (pattern_token, rank) pair; ~9 rows total.

The bot does not maintain rows here directly; this is hand-curated
reference data the wiki ships pre-populated. `UnitAttack` slots
reference the `attack_passive_id` enum; the wiki layer joins to render
the player-facing name and description.

**Why this is shared, not per-unit:** every Hydra / Lich Dragon /
Sweeping-pattern user sees the same Sweeping Strike text. Storing it
once and referencing it by id (instead of inlining the text on each
unit page) cuts duplicate spam from i18n storage and lets editors fix
typos in one place.

## Schema

```mediawiki
{{#cargo_declare:_table=AttackPassive
| attack_passive_id = String                                <!-- enum value referenced by UnitAttack slots -->
| pattern_token = String (allowed values=swipe,swirl,reach,rumble,tri_reach)
| rank = Integer                                            <!-- 1 = no falloff; 2 = -X% to additional targets -->
| name_sid = String                                         <!-- base_passive_strike_<token>_<rank>_name -->
| desc_sid = String
| display_name = String
| description = Wikitext
}}
```

## Field notes

- **`attack_passive_id`** is the primary key and the value `UnitAttack`
  rows reference (`default_passive`, `counter_passive`, `alt_passive`,
  `alt2_passive`). Stable, lowercase, snake_case.
- **`pattern_token`** is the L10n SID's family token. Drives the
  `name_sid` / `desc_sid` derivation. Five canonical families.
- **`rank`** distinguishes the falloff variant. Rank 1 = full damage to
  all hexes; rank 2 = additional targets take `–{0}%` damage (the
  percentage is unit-level — the `{0}` placeholder gets resolved per
  unit via `data.stats` blocks if present).
- **`name_sid` / `desc_sid`** point at L10n entries. The translation
  table joins on these.
- **`display_name`** / **`description`** are the resolved English
  defaults that render directly on the wiki without a join lookup.

## Canonical row contents

| `attack_passive_id` | `pattern_token` | `rank` | `display_name` | engine pattern_sid(s) |
| --- | --- | --- | --- | --- |
| `sweeping_strike` | swipe | 1 | Sweeping Strike | `attack_swipe_x100_x100` |
| `sweeping_strike_falloff` | swipe | 2 | Sweeping Strike | (rank-2 swipe; no current units use this) |
| `whirlwind_strike` | swirl | 1 | Whirlwind Strike | `attack_swirl_with_target_x100`, `attack_swirl_x1_x100` |
| `whirlwind_strike_falloff` | swirl | 2 | Whirlwind Strike | `attack_swirl_with_target_x50`, `attack_swirl_x2_x100` |
| `dragonbreath_strike` | reach | 1 | Dragonbreath Strike | `attack_reach_x1_x100_x100_with_delay`, `attack_reach_x1_x100_x100` |
| `dragonbreath_strike_falloff` | reach | 2 | Dragonbreath Strike | `attack_reach_x2_x100_x100_x100_with_delay` |
| `area_strike` | rumble | 1 | Area Strike | `attack_rumble_x1_x100`, `attack_rumble_without_self_x1_x100_x100` |
| `area_strike_falloff` | rumble | 2 | Area Strike | `attack_rumble_x1_x100_x50`, `attack_rumble_without_self_x1_x100_x50`, `attack_rumble_x2_x100` |
| `cone_strike` | tri_reach | 1 | Cone Strike | `attack_swipe_x100_x100_x2`, `attack_massive_x1_x100_x100_with_dalay` |

The engine pattern_sid → attack_passive_id mapping lives in
`extract/_pattern_passive_map.py`. Some mappings are non-trivial:
`attack_massive_*` → `cone_strike` is confirmed via Black Dragon's
Fighting Style ability text ("Performs a Cone Strike").

## Out of scope here

- **Piercing Strike** (`base_passive_strike_pierce_<rank>_*`) is **not**
  an attack-pattern passive. It's the player-facing name for the
  `attackPen` stat-passive and lives in the existing `stat_passive`
  synthesis path, not in `AttackPassive`.

## Related tables

- [`UnitAttack`](../UnitAttack.md) — references via `default_passive`,
  `counter_passive`, `alt_passive`, `alt2_passive` (N:1 each).
- [`AttackPassiveTranslation`](AttackPassiveTranslation.md) — joined
  on `attack_passive_id` (1:1).

## Wiki template notes

```mediawiki
<noinclude>
Reference table. One page per attack passive at
Data:AttackPassive/<attack_passive_id>. The actual #cargo_store call
lives in those data pages.
</noinclude><includeonly>{{#cargo_store:_table=AttackPassive
| attack_passive_id={{{attack_passive_id|}}}
| pattern_token={{{pattern_token|}}}
| rank={{{rank|}}}
| name_sid={{{name_sid|}}}
| desc_sid={{{desc_sid|}}}
| display_name={{{display_name|}}}
| description={{{description|}}}
}}</includeonly>
```

## Notes
