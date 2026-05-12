# LawLevelDef

One row per (law, level) pair. The 198 production laws contribute roughly 415 LawLevel rows (most laws have 2 levels; some have 1 or 3). Test laws add another ~80 rows.

Each level carries the law-points cost to enact (separate from the tier-unlock threshold), and the resolved description for *that level's* parameter substitutions. Bonuses awarded at this level are emitted as `{{BonusDef | parent_type=law_level | parent_id=<law_id>_L<level> | …}}` rows.

## Schema

```mediawiki
{{#cargo_declare:_table=LawLevelDef
| law_id = String
| level = Integer            <!-- 1-based; 1..max_level -->
| cost = Integer             <!-- law points to enact this level -->
| description = Wikitext     <!-- resolved English with this level's params -->
}}
```

## Field notes

- **Primary key is `(law_id, level)`**.
- **`cost`** is the per-level law-points spend, drawn from `parametersPerLevel[level-1].cost`. Each level's cost stands alone — leveling a law from L1 → L2 spends both costs in sequence.
- **`description`** is the parent law's `desc_sid` text resolved with this level's bonus parameters (via the new `CurrentFractionLawConfig` interpreter op, mirroring `CurrentMagicBattle` / `CurrentItem`).
- **No `name` column** — the law's name is shared across all levels and lives on `Law.name` / `TranslationDef`.

## Related tables

- [`LawDef`](LawDef.md) — joined on `law_id = Law.id` (N:1).
- [`BonusDef`](shared/Bonus.md) — joined on `parent_type='law_level' AND parent_id = law_id || '_L' || level`.
- [`LawLevelTranslationDef`](LawLevelTranslationDef.md) — joined on `(law_id, level)`. Carries per-level descriptions in 15 non-English languages.
