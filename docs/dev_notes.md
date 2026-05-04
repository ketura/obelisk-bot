# Dev notes

Hard-won lessons, deferred TODOs, and architectural patterns worth carrying
forward. Not formal decisions (those live in `decisions.md`) — more like
field notes from someone who has stepped on these rakes.

## Operational gotchas

### Bash-mount truncation gremlin

**Symptom:** Bash inside the workspace VM reads a Python file at N lines
when the canonical Windows-side file is N+200 lines. Running Python
through that mount sees the truncated view; AST parses fail with
"unexpected indent" or "unmatched bracket" partway through what looks
like valid code. A naive `cat >> file <<EOF` to "fix the missing tail"
duplicates content already present on the Windows side, corrupting the
Windows file with an orphan duplicate block.

**Why this matters:** caused several iterations of self-inflicted
damage during the D-021 work. Each fix made the file worse.

**Workarounds:**

- **For files over ~500 lines, use the `Edit` tool exclusively.** It
  writes through the Windows side directly and bypasses the mount lag.
- **If bash is the only option, do full-file rewrites** (`cat > file
  <<EOF ... EOF`) — never `>>` appends. A full rewrite syncs both
  sides at the same content; an append diverges.
- The bash mount sometimes catches up after an `Edit` write. If a
  quick `wc -l` shows the bash-side count is suspiciously low,
  cross-check with the `Read` tool (Windows-side authoritative)
  before patching anything in.
- If you've corrupted a file by appending duplicate content, the fix
  is to use `Edit` to delete the duplicated section (matching the
  exact orphan block to the empty/correct version).

The truncation appears to happen on writes that round-trip through
the mount, not just reads. Treat the mount as eventually-consistent
with delays of unknown magnitude.

## Architectural patterns

### L10n SID family naming as schema discovery

The single most useful technique for designing new reference tables
was greping the L10n corpus for player-facing names and reading off
the SID family that emerged.

For example, "Sweeping Strike" turned up at
`base_passive_strike_swipe_1_name`, which immediately revealed the
full family: `base_passive_strike_<token>_<rank>_{name,description}`,
covering 5 pattern tokens and 2 ranks. That family **is** the schema
for `AttackPassive` — we didn't need to invent rows, just read off
what the game already encodes.

**Use case:** when designing a new entity type's reference tables
(hero skills, magic schools, artifacts, etc.), grep the corpus for a
known player-facing name first. The naming convention will usually
reveal the full family.

The corpus lives at `<patch>/Core/Lang/english/texts/*.json` —
each file is `{"tokens": [{"sid": ..., "text": ...}, ...]}`. Use
`utf-8-sig` decoding (BOM-prefixed).

### Reference, don't duplicate

Mid-D-021 we pivoted from "synthesize a `UnitAbility` passive row on
each unit page for every pattern-passive" to "store one shared
`AttackPassive` row and have units reference it by id." The
realization: the pattern-passive name SIDs (`base_passive_strike_*`)
were already flowing through `views.passives[]` →
`Unit.shared_abilities`. Synthesizing rows would have duplicated
text on every page.

**Heuristic:** for any "many entities share this concept" design
question, trace the data flow first. If a SID is already reaching
the unit row through some path, prefer reference-by-id over local
duplication. The wiki layer's join cost is essentially zero
(Cargo's whole point) and the storage savings on i18n are large.

### Empirical archetype clustering before schema design

The `outputs/analyze_attack_archetypes.py` and
`outputs/crystallize_archetypes.py` scripts (kept in the bot's
scratch folder) clustered all 376 attack entries across 152 units by
canonical structural form. Result: 8 distinct mechanical shapes,
with most "differences" reducible to small dial overrides. That
clustering directly drove the slot-prefixed `UnitAttack` schema and
the `AttackArchetype` 3-row collapse.

**Use case:** for any "I have a pile of similar things, what's the
right way to model them" question, run the clustering analysis
before designing the table. The shape of the clusters dictates the
shape of the schema. The two scripts above are reusable templates —
adapt the canonicalization function to whatever entity is being
analyzed.

### "Shared seed" vs "per-patch" data

`docs/cargo/shared/` and `data/<table>/` (with `attacks/`,
`attack_passives/` so far) contain hand-curated wiki seed data,
**not** patch-extracted. The bot writes them on every emit, but the
content is governed by registries in code (e.g. `ATTACK_PASSIVES` in
`extract/_pattern_passive_map.py`), not by patch JSON.

The split is worth preserving as new entity types come online —
each will probably have its own seed-only reference tables (Skill
schools, magic colors, hero classes, etc.).

## Deferred TODOs

**`attackPen` → Piercing Strike rename.** The existing
`stat_passive` synthesis names the attackPen-derived passive
"Unyielding". The L10n corpus names it Piercing Strike I/II/III at
`base_passive_strike_pierce_<rank>_*`. Rank derives from the value:
0.3 → I, 0.4 → II, 0.5 → III. Currently affects Inquisitor family.
Fix is local to the stat_passive synthesis path.

**Provisional pattern_sid mappings.** Four entries in
`PATTERN_PASSIVE_MAP` are guessed against the swirl/rumble families
based on naming, with no live unit currently using them in the
2026-05-03 corpus:

- `attack_swirl_x1_x100` → `whirlwind_strike` (provisional)
- `attack_swirl_x2_x100` → `whirlwind_strike_falloff` (provisional)
- `attack_rumble_x2_x100` → `area_strike` (provisional)

If a future patch introduces a unit using one of these, a playtest
pass should confirm the mapping before the row ships to the wiki.

**`is_armed_ability` semantics.** We treat it as a flag derived from
the JSON tag prefix `armed_ability_*`. It correctly identifies
"Fighting Style" alts (Sulfurous Assault, Whirlwind, Arrow Barrage,
etc.) but the precise in-game mechanic it plugs into isn't
documented from our side. Worth a playtest pass to confirm what the
flag actually controls.

**Buff database.** `<slot>_buff_sid` on `UnitAttack` references buff
ids that don't yet have a Cargo table. ~52/376 attacks (14%) have a
buff slot populated. The buff content (duration, effect type, stat
mods) lives in `<patch>/Core/Lang/english/texts/unitsBuff.json` and
related shape JSONs. Medium-priority before the next entity type
lands; without it, "what does Aqualotl's debuff do" is
unanswerable from the wiki side.

**Damage modifiers.** `Unit.in_damage_mods` and
`Unit.out_damage_mods` are still opaque dict tuples on the model,
not emitted to Cargo. These encode "takes X% extra fire damage,"
"deals Y% extra to undead," etc. — exactly the kind of data players
filter on. Either flat list-of-string columns or a side table would
work.

**Faction laws nested arrays.** Open question from `decisions.md` —
`fractionLawsLines: [{groups: [{laws: [...]}]}]` doesn't fit Cargo's
flat schema. Will need a side table or list-typed columns when the
faction-laws entity gets attention.

## Useful scripts in the outputs folder

- `analyze_attack_archetypes.py` — clusters entries by canonical
  hash, shows top archetypes + singletons + per-field variation.
  Adapt the normalization function for any entity type.
- `crystallize_archetypes.py` — second-pass clustering with
  unit-suffix stripping; identifies "this is the same shape with a
  unit-name suffix" cases.

Both are stdlib-only Python; no project imports needed. Run with
the `python3` in the workspace VM (or any local Python 3.10+).

## A note on the editor pattern that worked

Across the D-021 cycle, the iteration that consistently produced
good output was:

1. **Inspect.** Grep the L10n corpus, sample a few unit JSONs, count
   distinct values.
2. **Cluster.** Run a clustering pass to see how many real shapes
   exist vs. how many superficial "differences" there are.
3. **Discuss.** Surface the cluster picture, propose a couple of
   schema shapes with their trade-offs, get a decision.
4. **Implement small.** Model + extract + emit, in that order.
5. **Run end-to-end on the full corpus.** Look at sample output.
6. **Iterate on real data.** "Hydra is missing X" → "I see why — X
   lives in `views.alternativeAttacks`, not where I was looking."

The "look at sample output" step caught issues that pure design
review would have missed (e.g. the per-slot rows that Repeated
identity columns awkwardly; the over-broad pattern_sid emission
that didn't tell wiki readers anything useful).
