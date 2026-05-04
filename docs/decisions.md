# Architectural Decisions

Locked decisions captured at scaffolding time. Updates as design evolves should append, not overwrite — keep the history.

## D-001 — Language: Python

**Date:** 2026-05-01
**Status:** Locked.

We're shipping a public-release wiki bot. The Python ecosystem (pywikibot, mwclient, pydantic) is the canonical fit, lower-friction for casual contributors, and avoids any GPL-3 entanglement with [OldenEraExplorer](https://github.com/laszlo-gilanyi/OldenEraExplorer).

**Considered and rejected:**
- C# / .NET — would let us crib OEE's `Domain` entities and `Localization/Scripting` resolver wholesale, but contaminates our license (OEE is GPL-3.0) and shrinks the contributor pool. The "C# isn't a scripting language" objection isn't load-bearing for a tool that's read-JSON → emit-wikitext → POST-API.
- Node/TypeScript — `mwn` is solid, but Python's pydantic data-modeling story is decisively better for this shape of work.

## D-002 — License: Apache 2.0

**Date:** 2026-05-01
**Status:** Locked.

Permissive enough for community uptake, with the patent-grant clause that MIT lacks (matters if upstream Olden Era devs ever contribute). One-way compatible with GPL-3 — OEE devs can fold our code into theirs; we cannot pull theirs into ours. Acceptable.

## D-003 — Placeholder resolver: not in v1

**Date:** 2026-05-01
**Status:** Locked.

OEE re-implements the game's script engine to resolve `{0}`/`{1}`/etc. placeholders in description text. We don't need this for Cargo data: the structured fields (stats, costs, IDs, tiers) carry no placeholders, and translatable description templates can be stored in Cargo as raw `{0}`-bearing strings. Display layer or human authors handle resolution.

If resolution becomes critical for some category later, two paths:
1. Shell out to OEE's CLI as a subprocess (separate-process aggregation, GPL-safe).
2. Port `Localization/Scripting/` (~2k LOC) to Python.

## D-004 — Wiki access: existing wiki, no bot account yet

**Date:** 2026-05-01
**Status:** Locked.

Target: `https://oldenera.wiki.gg/` (placeholder until bot account exists). Until then the uploader writes to local files only; the upload phase scaffold is stubbed.

## D-005 — Page granularity: one page per entity

**Date:** 2026-05-01
**Status:** Locked.

Each entity gets one wiki page (e.g. `Data:Unit/Angel`) hosting all of its data — invariant `#cargo_store` row plus all 16 localization rows. Atomic per-entity update; one page edit = one consistent transaction.

**Considered and rejected:**
- Subpages per language (`Data:Unit/Angel/en`, `…/ru`) — clean for translator workflows, but multiplies page count by ~16 and complicates atomic updates.
- Mega-pages per category — too large, edit-conflict prone.

## D-006 — i18n schema: single global Localization table

**Date:** 2026-05-01
**Status:** Locked.

The source data is already shaped this way: every L10n file under `Core/Lang/<lang>/texts/*.json` is a flat `(sid, text)` mapping. Empirical: 12,497 SIDs in English, exact parity across all 14 languages (Russian off by 1 — typo, not a translation gap).

**Cargo schema:**
- `Localization(sid String, language String, text Text, source_kind String)` — one row per (sid, language). ~175k rows total.
- Per-entity invariant tables (`Unit`, `Spell`, `Hero`, …) reference SIDs in dedicated columns (e.g. `Unit.name_sid`).
- Display-side queries join: `tables=Unit,Localization | join on=Unit.name_sid=Localization.sid | where=Localization.language='en'`.

**Where rows live (page sense):**
- For SIDs an entity "owns", the L10n rows are stored on that entity's page (`Data:Unit/Angel` includes its 14× SID rows for `angel_name`, `angel_desc`, `angel_class_*`, plus its abilities' SIDs).
- For orphan SIDs (UI strings, biome names, etc. that no specific entity claims), they go to bucket pages: `Data:Localization/UI`, `Data:Localization/Misc`, etc.

**SID ownership rule:** discover from JSON (walk for `*Sid`/`*_sid` fields and explicit SID slots) + supplement with convention (`<id>_name`, `<id>_desc`) + log orphans for the bucket pages.

## D-007 — Languages: all 16 from v1

**Date:** 2026-05-01 (originally said 14; corrected to 16 on 2026-05-01 after extracting against real data)
**Status:** Locked.

Given source parity is essentially perfect (12,497 SIDs in every language with no gaps), ingesting all 16 from day one costs us bytes, not architecture. Languages observed in the 2026-04-30 corpus: BRportugese, czech, english, french, german, hungarian, italian, japanese, korean, polish, russian, spanish, turkish, ukrainian, zhCN, zhTW.

OEE's README claims 14; the data ships 16 (zhCN and zhTW are distinct, and BRportugese is its own dir). Trusting empirics over secondary claims.

## D-008 — Diff scope: everything in JSON

**Date:** 2026-05-01
**Status:** Locked.

Stat changes, ability changes, cost changes, English text changes, non-English translation changes, asset references. Every field reachable from the canonical record types is in scope for the diff engine. We can decide later how to *render* translation churn in patch notes (probably summarized rather than enumerated), but it's all detected.

## D-009 — Tooling: modern stack

**Date:** 2026-05-01
**Status:** Locked.

- Runtime: pydantic v2, mwclient, typer, rich
- Dev: ruff, mypy strict, pytest
- Env: stdlib `venv` + `pip` (no uv required; uv works fine if developer prefers)
- Python: 3.10+ (see horizon note below)

The diff is hand-rolled, not `deepdiff`. Wikitext is f-string-rendered, not jinja. Both decisions are about *quality of output*, not avoiding deps for their own sake.

**Python 3.10 horizon note (2026-05-01):** Floor was originally 3.11 but lowered to 3.10 to match the assistant's sandbox runtime. CPython 3.10 reaches EOL October 2026; revisit and bump the floor to 3.11+ when the sandbox upgrades or before the project's first stable release, whichever comes first. The only feature this floor change cost us was `enum.StrEnum` (replaced with `class Faction(str, Enum)` — equivalent for our uses).

## D-010 — First entity end-to-end: Units

**Date:** 2026-05-01
**Status:** Locked.

Units are the richest category (stats, abilities, passives, costs, upgrades, faction, biome, AI tags). Driving Units end-to-end first will surface the architecture's edge cases. Other categories follow once the framework settles.

## D-011 — OEE is a peer reference, not authoritative

**Date:** 2026-05-01
**Status:** Locked.

OldenEraExplorer was built against the demo and only partially updated for the released game (per ketura). When OEE's data model and the source JSON disagree, the **JSON is ground truth, OEE is a hint**.

This came up concretely twice already:

* OEE's `AbilityRef` type carries `NameSid` / `DescriptionSid` fields that don't exist in source unit JSON. We initially modeled abilities the same way and it was wrong. (Resolved by separating JSON logic blocks from L10n-discovered SID slots — see D-012.)
* Unit-level descriptions were claimed to live under `<id>_description`; they actually live under `<id>_narrativeDescription`. OEE may not have updated for this either.

**Practical implication:** when designing extractor logic for a new entity kind, sample real source data first, *then* glance at OEE for confirmation/contrast. Don't start from OEE's model and back-fit the JSON to it.

## D-012 — Unit named-ability SIDs: discovered from L10n, not from JSON

**Date:** 2026-05-01
**Status:** SUPERSEDED by D-015. We now read ``Core/DB/units/units_views/<faction>/<id>_v.json`` directly — it lists the unit's named abilities/passives explicitly with name and description SIDs. The original heuristics (regex + ordinal discovery + JSON-block-to-SID correlation) are gone.

The source unit JSON describes abilities/passives as logic graphs with no `nameSid` field. The L10n corpus contains SIDs of the form `<id>_(ability|passive|buff|debuff|selfbuff)_<N>_(name|description)` — but the ordinals don't map cleanly to JSON list indices: angel has 4 JSON passives but only 2 named-passive SIDs, because the JSON list mixes player-visible passives with internal mechanic-implementation flags (`data.disablers`, immunity bundles).

**Resolution:** maintain two parallel structures on each unit, with no claimed 1:1 mapping:

1. **`passives` / `abilities`** — JSON logic blocks, opaque, preserved verbatim. Drives diffs of mechanic changes.
2. **`named_ability_slots`** — discovered from the L10n corpus by walking SIDs matching the convention. Each slot is `(kind, ordinal, name_sid, description_sid)`. Drives L10n storage and gives the display layer a clean list of named ability slots to query.

The JSON-block-to-SID-ordinal reconciliation is deferred to the future Ability category, where we can fingerprint structurally across all units. May or may not be solvable without help from the OE devs.

## D-013 — Wiki output goes through helper templates, not raw Cargo syntax

**Date:** 2026-05-01
**Status:** Locked. Per-entity-kind template hierarchy design is an ongoing effort.

`#cargo_store` and `#cargo_declare` syntax is hostile to non-technical wiki editors. The bot emits data through a layer of helper templates instead. Pattern, per entity kind:

**Master template** (e.g. `Template:Unit`) owns the schema. It declares `#cargo_declare` for the entity's Cargo table, accepts every possible field as a named parameter with appropriate optional-default handling, and internally calls `#cargo_store` to write the row. Editors who invoke `{{Unit | id=angel | hp=225 | ...}}` never see Cargo syntax.

**Subset templates** narrow the parameter list for common archetypes — e.g. `Template:RangedUnit`, `Template:MeleeUnit`, `Template:MidRangeUnit`, or `Template:BaseUnit` / `Template:UpgradedUnit`. A subset template fills in the master template's parameters with sensible defaults for fields the archetype doesn't use, so editors see only the parameters that actually matter for their case. Subset clusters are designed empirically per entity kind by clustering real records.

**Emitter behavior:**

* For each canonical record, pick the *most specific* template that fits. If a unit qualifies as a `RangedUnit`, emit `{{RangedUnit | ...}}`, not `{{Unit | ...}}`.
* Output order is deterministic and stable: a fixed field order within each template invocation, and a fixed template order on multi-store data pages. This makes "did this page change?" trivially diffable both for the bot's own diff engine and for human reviewers comparing wiki revision history.
* Data pages (`Data:Unit/<id>` etc.) are **bot-owned**. Discrepancies between wiki state and source JSON should be fixed by updating the extractor or the emitter, not by editing the data page by hand. Display articles that query Cargo are the human-edited surface.

**Implications for our codebase:**

1. The emitter needs a per-entity-kind *template registry*: a Python data structure mapping template name → ordered parameter list → mapping rule from canonical record fields to template parameters.
2. The emitter needs a *classifier*: given a canonical record, return the most specific template whose preconditions it satisfies. Preconditions are predicates over the record (e.g. "has only ranged attack" → `RangedUnit`).
3. Template definitions on the wiki side are out of scope for this project — someone else writes the wikitext for `Template:Unit` etc. We design the schema (field names, types, defaults) and produce invocations.

**Parameter style:** named parameters everywhere. ``{{Unit | id=angel | hp=225 | ...}}``, never positional. Eliminates ordering as a correctness concern (the bot still emits in a stable order for diff readability, but ordering becomes cosmetic, not load-bearing).

**Sparseness:** the emitter omits fields whose source JSON didn't define them. Empty/null values are not emitted. Reasoning: parameter lists for the master template will be large; sparse output keeps real-world data pages readable, and the diff engine handles "added line" vs "modified line" identically — there's no diff-quality advantage to verbose output. Concretely, "default" means *absent in source*, not *equal to a Python default value*; numeric stats like ``morale=0`` are still emitted because the source set them, while truly absent fields stay out.

**Cross-reference:** D-006 describes data pages as containing ``#cargo_store`` rows; D-013 supersedes that surface description (the wikitext is template invocations now), but the underlying Cargo schema D-006 specifies is unchanged — the templates ultimately call ``#cargo_store`` internally.

**Open per-entity work** (will accumulate as D-013-N as we tackle them):

* D-013-Unit (TBD) — full Unit field set, subset template clusters, classifier predicates.
* D-013-Spell, D-013-Hero, D-013-Artifact, etc. — same exercise per category.

## D-014 — Upgraded units inherit named ability slots from their base

**Date:** 2026-05-01
**Status:** SUPERSEDED by D-015. Each upgrade variant has its own views file with its own explicit ability/passive list. There is no inheritance — each variant emits exactly what its views file enumerates. The empty-page-on-upgrade behavior described below was an artifact of the old SID-prefix-matching scheme.

In Olden Era, an upgraded unit (``phoenix_upg``, ``angel_upg``, etc.) only
redefines ``<id>_name`` and ``<id>_narrativeDescription`` in the L10n corpus.
Its abilities and passives use the **base unit's** named-slot SIDs
(``phoenix_passive_1_name``, not ``phoenix_upg_passive_1_name``). Empirically
confirmed against ``phoenix``/``phoenix_upg``/``phoenix_upg_alt``: 7 / 0 / 0
named slots discovered respectively. Same holds for other unit chains.

**Implications:**

1. **Empty `UnitNamedSlot` and `UnitNamedSlotTranslation` tables on upgrade
   pages are correct,** not a bug to fix. Don't try to populate them from
   the base — that would duplicate data and require synchronization on
   patches.
2. **Display layer queries follow the ``base_sid`` chain.** When rendering
   an upgraded unit's ability list, the template walks
   ``Unit.base_sid -> Unit.base_sid -> ...`` until ``base_sid`` is empty,
   then queries `UnitNamedSlot` / `UnitNamedSlotTranslation` for whichever
   ancestor owns the slots. Cargo's recursive query support is limited;
   may need template-level recursion or a flattened resolved view.
3. **Diff engine awareness:** when a base unit's named-slot text changes,
   the upgrade variants are *visually* affected even though their own rows
   don't change. The patch-notes generator should surface "ability
   description changed on `phoenix`, affects `phoenix_upg` and
   `phoenix_upg_alt`" — that's a reporting-layer concern, not a schema one.

**Side observation (not a decision, just noted):** ``upgradeSid`` in source
forms a chain (``phoenix.upgradeSid = phoenix_upg``,
``phoenix_upg.upgradeSid = phoenix_upg_alt``) rather than a binary fork from
the base. The game presents these as alternative upgrade choices in UI, so
the chain is likely vestigial source data; we faithfully store what's there
and let display decide.

## D-015 — Views file is the authoritative SID source per unit

**Date:** 2026-05-02
**Status:** Locked. Supersedes D-012 and D-014.

Each unit has a ``Core/DB/units/units_views/<faction>/<id>_v.json`` file that
explicitly lists its named abilities and passives:

```json
"abilities": [
    {"name": "godslayer_ability_1_name", "description": "godslayer_ability_1_description", ...}
],
"passives": [
    {"name": "base_passive_melee_attack_name", ...},
    {"name": "demon_passive_1_name", ...},
    {"name": "godslayer_passive_1_name", "description": "godslayer_passive_1_description_upg", ...}
]
```

Each entry has explicit ``name`` and ``description`` SIDs — no heuristic,
no ordinal discovery, no positional fallback. Variant-specific descriptions
(``_description_upg``, ``_description_upg_alt``) are pre-resolved by the
views file itself; we just take the SID and look up the L10n entry.

**Practical implication:** the entire heuristic stack (match/patterns,
match/registry, alt-upgrade ordinal jumps, variant SID fallback, family
inheritance) is dead code. Removed.

The views file is the *display layer* — what the player sees. The logic
file is still the source of truth for stats, mechanics, and the diff
engine. We use both, with views authoritative for which abilities
exist and logic authoritative for what they do.

## D-016 — Base and faction passives are NOT stored on each unit's page

**Date:** 2026-05-02
**Status:** Locked.

The views file's passive/ability lists include three flavors of SIDs:

* **Unit-specific** (``godslayer_passive_1_*``, ``angel_ability_1_*``):
  STORED on the unit's page as full ``UnitAbility`` rows + translation
  rows.
* **Universal base passives** (``base_passive_melee_attack_*``,
  ``base_passive_flyer_*``, ``base_passive_staunch_<rank>_*``): DROPPED.
  Recovered by the wiki display layer from unit attributes (creature_type,
  move_type, attack_penetration, etc.). Stored once in a shared
  ``Data:BasePassive`` table — emission is Phase 2 work.
* **Faction-shared passives** (``demon_passive_1_*``, ``human_passive_2_*``):
  DROPPED. Recovered via the unit's ``faction`` enum. Shared
  ``Data:FactionPassive`` table — also Phase 2.

Filtering rule: drop any name SID whose prefix is ``base_`` or matches a
known faction id (one of: human, undead, dungeon, nature, demon, unfrozen,
neutral). Everything else is unit-specific.

**Why drop them:** these passives are repeated across dozens of units. A
demon faction passive applies to ~20 demon units; storing 20 copies of the
same name + 16 translations is pure duplication. The shared tables hold
each definition once.

## D-017 — Audit reports JSON content not represented in views

**Date:** 2026-05-02
**Status:** Locked. Replaces the heuristic-driven audit from D-013/early audit work.

The audit's job is now narrow: **compare the unit's logic JSON against its
views file and surface anything in the logic that isn't reflected in the
views.** Examples:

* A passive block in ``logic.passives[]`` whose mechanic doesn't appear in
  ``views.passives[]`` (could be internal-only, or could be a missing views
  entry — worth flagging).
* A stat field in ``logic.stats`` (e.g. ``outDamageIfLevelAbove``) that no
  named view passive corresponds to.
* Any ability in ``logic.abilities[]`` that has no matching ``views.abilities[]``
  entry.

The audit does not drive emission anymore; it's purely a sanity-check
report (``out/audit.json``). Maintainers review it after each patch to
catch new patterns Unfrozen ships that we don't yet handle.

## D-018 — Patch-cycle pipeline (diff + upload)

**Date:** 2026-05-03
**Status:** Locked.

The patch-cycle command takes a new core-JSON dump plus the previous patch's
emitted wiki output and produces:

1. **Fresh emit** of the new patch's wiki pages (reuses the existing emit pipeline).
2. **Per-page wiki diff** for every page that changed between previous and new
   emit. Stored locally as drilldown files (`<out>/diff/changed_pages/<id>.diff`),
   not uploaded.
3. **Deep JSON diff** between the two core dumps, written to
   `<out>/diff/json_diff.txt`. Operator-only artifact for data miners; never
   uploaded. The wiki-text diff is the right filter for "did the player-visible
   thing change"; the JSON dump is for forensic debugging.
4. **Patch article** at `Data:Patches/<date>` listing all changed data pages
   as wiki links, grouped by entity type.
5. **Operator summary** (`<out>/diff/summary.md`) — table of changed pages,
   line-count deltas, etc.

Default mode is **dry-run**: artifacts are written, nothing is uploaded.
`--force-upload` actually pushes the changed wiki pages and the patch article.

**Previous output is supplied by the user** as a folder path. The bot does not
re-emit the old patch. (If they want a fresh old emit, they run `emit-all-units`
on the old patch dump first.) This keeps the cycle command's I/O explicit and
caching-free.

**Wiki credentials** live in a project-local `artificer.toml` (gitignored), not
env vars. Keeps multi-environment setups straightforward.

## D-020 — Unused-unit detection: english-name signal only

**Date:** 2026-05-04
**Status:** Locked.

`Unit.unused = True` is set during enrichment when the unit's primary
`name_sid` has no English entry in the localization corpus. In the
2026-05-03 corpus that catches exactly 5 deprecated units: `dragon`,
`dragon_upg_alt`, `avatar_nature`, `avatar_unfrozen`, `peasant_normal`.
The flag emits as `unused = yes` in the wiki row, omitted otherwise so
queries can filter `WHERE unused != "yes"` without weighing down the
common case.

**Why only this signal, no manual override list:**
The community has identified additional units the game doesn't actively
use (jaw family, lava_larva, trick_demon_upg/_upg_alt) but their data
layer is fully populated — full English name, description, AI archetype,
gold cost, abilities. The data was kept after model reworks: jaw was a
zerg-like creature reworked into a scorpion; trick_demon's base form was
rebranded as the neutral `gnat`. The unit data is still active for the
gameplay system; only the visual assets were swapped.

There is no JSON-side signal that distinguishes "data-active unit with
swapped model" from "data-active unit with original model", so we don't
attempt to flag those as unused. False-negatives there are the right
tradeoff — claiming a unit is unused when it might be referenced by
gameplay paths we don't see is worse than missing a few cosmetic
deprecations.

**Future work (deferred): unused-asset detection.** A separate pipeline
that inspects Unity asset bundles could find icons/meshes that no JSON
references, or vice versa. Would require AssetRipper-style asset
extraction (OEE bundles this). Out of scope for the current data layer.

## D-021 — UnitAttack: shared reference tables + one per-unit fat row

**Date:** 2026-05-04
**Status:** Locked. Revised same-day after first cut.

Empirical analysis of the 2026-05-03 patch found 376 attack entries
across 152 units boil down to a small fixed structure plus a few dials.
The split:

1. **`AttackArchetype`** — hand-curated reference table, **exactly 3
   rows** (`melee`, `ranged`, `reach`). Each row carries the canned
   per-attack-type passive name and description that every unit's
   tooltip inherits ("Melee Attack — Can only attack adjacent enemies.
   Provokes counterattacks."). Names align with the L10n family
   (`base_passive_melee_attack_*`, `base_passive_ranged_attack_*`,
   `base_passive_remote_attack_*`). Note: JSON `attackType_=range` =
   player-facing "Long Reach" = bot enum `reach`. Translations live in
   `AttackArchetypeTranslation`.

2. **`UnitAttack`** — **one row per unit** (revised; was per-slot).
   All four attack categories — `default`, `counter`, `alt`, `alt2` —
   collapse into a single wide row with slot-prefixed fields
   (`default_attack_type`, `counter_stat_dmg_mult`, `alt_passive`, etc.).
   Each slot has its own role-aware defaults; the bot sparse-emits only
   fields where the unit deviates.

3. **`AttackPassive`** (shared, ~9 rows) — Sweeping Strike, Whirlwind,
   Dragonbreath, Cone, Area Strike + falloff variants. These appear in
   player tooltips as passives but exist purely as a side-effect of the
   unit's `attack_pattern_sid`. Each `UnitAttack` slot references one
   via `<slot>_passive` (e.g. `default_passive=sweeping_strike`). The
   wiki layer joins on `attack_passive_id` to render the player-facing
   name and description. **Pattern-passives are no longer synthesized
   as `UnitAbility` rows** — that duplicated the same name/desc on
   every Hydra-and-friends page. Reference > duplication.

4. **`shared/` subfolder** under `docs/cargo/` collects the
   reference-data tables (`AttackArchetype`, `AttackArchetypeTranslation`,
   `AttackPassive`, `AttackPassiveTranslation`). These are hand-curated
   wiki seed data, not patch-extracted; segregating them keeps the
   per-patch table list focused.

**Naming flip:** the bot's enum uses `melee` / `ranged` / `reach`,
matching player-facing terminology. JSON values map: `melee → melee`,
`shoot → ranged`, `range → reach`. The L10n SID for "reach" lives
under `base_passive_remote_attack_*` — the data-side name there is
"remote", but the wiki uses "Long Reach" / `reach` consistently.

**Per-slot defaults** live on each slot prefix (`default_*` defaults to
1.0× / triggers counter; `counter_*` to 1.0× / no counter; `alt_*` and
`alt2_*` to 0.5× / no counter). Bot suppresses fields that match the
slot's default. A typical Crossbowman row emits ~8 fields total across
all four slots; a basic Peasant emits ~4.

**Explicitly out of scope:** projectile range/falloff/ammo
(`shootRange`, `shootThreshold`, `shootRedCount`, `shootDmgBuff`) and
`target_mechanics` arrays. Stable enough that freeform wiki copy on the
rare deviating unit is cheaper than schema weight.

**Why not fold attacks into UnitAbility:** attacks and abilities share
the underlying combat engine (identical `damageDealer` shape), but the
player-facing distinction is real — "what this unit does as its baseline
hit" vs. "what special things it can do." Separate tables match how the
wiki renders them and how readers think about them.

**Pattern_sid mapping is hand-curated, not auto-derived.** Several
mappings are non-trivial — `attack_massive_x1_x100_x100_with_dalay_*`
maps to Cone Strike (`base_passive_strike_tri_reach_1_*`) despite no
shared token. Confirmed via Black Dragon's `black_dragon_ability_1`
description ("Performs a Cone Strike"). Unconfirmed mappings (a handful
of `_x2` and `swirl_xN` variants) are flagged with `# TODO` placeholders
in code; the bot synthesizes a clearly-named placeholder passive
(`pattern_passive_TODO_<pattern_sid>`) and logs a warning so the
mismatch is visible in wiki output and easy to resolve later.

**Future work:** Fighting Style abilities (Hydra: Whirlwind Strike;
Medusa: Arrow Barrage; Black Dragon: Sulfurous Assault; etc.) are alt
attacks the L10n names with unit-specific SIDs `<unit>_ability_<N>`,
sharing the SID namespace with entries in the JSON `abilities[]` array.
The current ability extraction needs to learn that an alt-attack on
some units owns the next-available `<unit>_ability_<N>` slot. Separate
decision when we tackle that.

**Piercing Strike is a stat-passive, not an attack-pattern.** The L10n
family `base_passive_strike_pierce_<rank>_*` exists, but no unit has an
`attack_pierce_*` pattern_sid. "Piercing Strike I/II/III" is the
player-facing name for the `attackPen` stat passive (rank derives from
the value: 0.3 → I, 0.4 → II, 0.5 → III). The current `stat_passive`
synthesis with the placeholder name "Unyielding" should be updated to
use the `pierce` family.

## Open questions / known unknowns

- **Faction laws have nested arrays** (`fractionLawsLines: [{groups: [{laws: [...]}]}]`). Cargo doesn't natively support nested structures; will need either a side table with foreign keys or list-typed fields. Cross when we get there.
- **`fraction` vs `faction`** — source JSON uses "fraction" (likely a translation artifact); we normalize to "faction" on extract. OEE's domain entities also normalize this.
- **Bot account creation** — blocking the upload phase. User to create when we're closer to that milestone.
- **Bucket page structure for orphan SIDs** — exact split (one big page? per-source-file?) deferred until we know the orphan distribution.
