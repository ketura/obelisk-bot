# AttackArchetype

A tiny reference table — **exactly 3 rows**, one per attack-type
category. Provides the canned name and description that every unit's
default-attack panel inherits ("Melee Attack — Can only attack adjacent
enemies. Provokes counterattacks.").

The bot does not extract or maintain rows here; this is hand-curated
reference data the wiki ships pre-populated. `UnitAttack` rows reference
this table via the `attack_type` enum.

## Schema

```mediawiki
{{#cargo_declare:_table=AttackArchetype
| attack_type = String (allowed values=melee,ranged,reach)
| display_name = String
| description = Wikitext
| name_sid = String
| desc_sid = String
}}
```

## Field notes

- **`attack_type`** is the primary key. Three rows total: `melee`,
  `ranged`, `reach`. The bot translates JSON `attackType_` values to
  these labels on emit:
  - JSON `melee` → `melee`
  - JSON `shoot` → `ranged`
  - JSON `range` → `reach`
- **`name_sid` / `desc_sid`** point at the canonical L10n entries the
  wiki ships English defaults from. These also serve as the join keys
  to `AttackArchetypeTranslation`.

## Canonical row contents

These are the exact values the wiki ships in pre-populated rows.

| `attack_type` | `display_name` | `name_sid` | `desc_sid` | `description` |
| --- | --- | --- | --- | --- |
| `melee` | Melee Attack | `base_passive_melee_attack_name` | `base_passive_melee_attack_description` | Can only attack adjacent enemies. Provokes counterattacks. |
| `ranged` | Ranged Attack | `base_passive_ranged_attack_name` | `base_passive_ranged_attack_description` | Can attack enemies at any range. Replaced with a weaker Melee attack if an enemy is adjacent. (Specific falloff numbers are unit-level; the canned text uses `{0}`/`{1}`/`{2}`/`{3}` placeholders.) |
| `reach` | Long Reach | `base_passive_remote_attack_name` | `base_passive_remote_attack_description` | Has an attack that targets the hex directly behind an adjacent hex. It doesn't provoke counterattacks and doesn't move the attacker next to their target. |

The L10n family carries variant SIDs for special cases (e.g.
`base_passive_melee_attack_no_counter_*` for melee that doesn't provoke
counterattacks; `base_passive_ranged_attack_no_close_*` for ranged
without melee penalty). For Phase 1 we collapse to the three primary
rows; per-unit deviations from the canned text get conveyed via *other*
synthesized passives (Quickness, Sharpshooter, Countershot, etc.) on the
unit's passive list.

## Related tables

- [`UnitAttack`](../UnitAttack.md) — references `attack_type` (1:N).
- [`AttackArchetypeTranslation`](AttackArchetypeTranslation.md) —
  joined on `attack_type` (1:1) for the 15 non-English locales.

## Wiki template notes

```mediawiki
<noinclude>
Reference table for the three attack-type categories. One page per
attack_type at Data:AttackArchetype/<attack_type>. The actual #cargo_store
call lives in those data pages.
</noinclude><includeonly>{{#cargo_store:_table=AttackArchetype
| attack_type={{{attack_type|}}}
| display_name={{{display_name|}}}
| description={{{description|}}}
| name_sid={{{name_sid|}}}
| desc_sid={{{desc_sid|}}}
}}</includeonly>
```

## Notes
