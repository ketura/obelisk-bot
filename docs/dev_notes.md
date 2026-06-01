# Dev notes

Hard-won lessons, deferred TODOs, and architectural patterns worth carrying
forward. Not formal decisions (those live in `decisions.md`) — more like
field notes from someone who has stepped on these rakes.

## Operational gotchas

### Bash-mount truncation gremlin

> **TL;DR — read this before editing any source file in this repo.**
>
> The `Edit` and `Write` tools silently truncate non-trivial edits to
> files over ~30 KB (and sometimes smaller). The file looks fine to the
> `Read` tool but the bash-mount view — which is what Python actually
> compiles — is missing its tail. A stale `.pyc` then masks the damage,
> so `obelisk extract` "succeeds" while running pre-edit code.
>
> **Do not use `Edit`/`Write` for non-trivial edits. Use a bash-Python
> full-file patch instead, every time:**
>
> ```bash
> .venv-sandbox/bin/python << 'PYEOF'
> from pathlib import Path
> import ast
>
> def patch(path, old, new, count=1):
>     p = Path(path)
>     src = p.read_text()
>     n = src.count(old)
>     if n != count:
>         raise AssertionError(f"{path}: anchor matched {n}x, expected {count}")
>     p.write_text(src.replace(old, new))
>
> patch("src/obelisk/extract/unit.py", "<exact old text>", "<exact new text>")
> # ...more patch() calls...
>
> ast.parse(Path("src/obelisk/extract/unit.py").read_text())  # verify
> PYEOF
> ```
>
> **Why it works:** `Path.write_text()` is one full-file write — it
> syncs both mount sides at identical content. `Edit`/`Write`
> round-trip a diff through the mount and the tail gets dropped. The
> single-match `count` assertion makes a stale anchor fail loudly
> instead of silently mis-patching; the trailing `ast.parse()` catches
> any damage on the spot. Whole-new files are fine to create with the
> `Write` tool — the truncation only bites edits that grow an existing
> large file.
>
> This exact method has been re-derived from scratch in at least four
> separate sessions (D-021, D-040, the skill-roll work, the
> attack-archetype work). It works. Reach for it first. Escalate to the
> git-archive mirror recipe (further down) only when a file is
> *already* corrupted on disk and you need a known-good baseline.

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

- ~~**For files over ~500 lines, use the `Edit` tool exclusively.**~~
  '''SUPERSEDED''' — see the TL;DR box above. The `Edit` tool is *not*
  reliable for large files; it was the original (wrong) guess and cost
  multiple sessions. Use the bash-Python full-file patch.
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

**Update from later sessions** — additional patterns observed beyond
the original entry:

- **Null-byte tails, not just truncation.** Some "truncated" writes
  actually replace the lost tail with literal ``\x00`` bytes. A naive
  ``text.rstrip()`` won't catch them (rstrip recognizes whitespace
  characters, not nulls), and Python text-mode reads with
  ``errors="replace"`` silently turn the nulls into U+FFFD which
  survive whitespace stripping. The fix is byte-mode: read with
  ``Path.read_bytes()``, strip ``b"\x00 \t\n\r"`` from the right,
  rewrite with ``Path.write_bytes()``. Tell-tale that null-bytes are
  the cause: ``ast.parse()`` raises ``ValueError: source code string
  cannot contain null bytes``, or ``grep`` starts reporting the file
  as binary.

- **The Edit tool isn't a guaranteed workaround.** The original entry
  recommends ``Edit`` over ``cat >> file``, which is generally true,
  but ``Edit`` calls can return success and still leave the on-disk
  file truncated for the same handful of files repeatedly. Some files
  (during the cargo template work: ``ArtifactDef.wiki.txt``,
  ``SpellRankDef.wiki.txt``, ``shared/BonusDef.wiki.txt``) consistently
  re-truncated themselves across multiple ``Write`` / ``Edit`` cycles
  even after a clean rewrite. Common factors among the persistent
  victims: file size in the 3-5 KB range, contents include
  ``<noinclude>``/``<includeonly>`` template syntax, frequent edits in
  short succession.

- **Working fallback: direct binary write through bash Python.** When
  ``Edit`` / ``Write`` persistently truncate a specific file, drop to
  bash and write via Python's binary file API:

  ```bash
  python3 << 'PYEOF'
  content = b"...full file body as bytes..."
  with open("path/to/file", "wb") as f:
      f.write(content)
  PYEOF
  ```

  This bypasses the editor-tool persistence layer and writes through
  to the Windows-side file in one shot. After the write, verify with
  ``Path.read_bytes()`` that the on-disk size matches what was
  written.

- **Cross-check via Read.** Whenever a bash check (``wc -l``,
  ``grep -c``, ``ast.parse``) reports something suspicious, validate
  against the ``Read`` tool before reacting. Roughly 80% of the
  "issues" reported by bash-side checks during the cargo work were
  bash-mount staleness, not actual file damage. The fingerprint of a
  genuine issue is: ``Read`` shows the same problem the bash check
  does.

**Update from the D-040 translation refactor** — a reliable workflow
that beat the gremlin across a ~25-file change:

- **The git object store is trustworthy; the working-tree mount is
  not.** ``git archive HEAD`` and ``git show HEAD:<file>`` read from
  content-addressed blobs and return byte-perfect committed content,
  bypassing the mount entirely. ``cp`` / ``cat`` / ``dd`` / ``stat``
  on a working-tree path all see the same stale/truncated/null-padded
  view the mount is currently serving.

- **Distinguish phantom truncations from real edits.** ``git status``
  will flag mount-truncated files as "modified". To tell a gremlin
  artifact from a genuine uncommitted change: a phantom truncation's
  worktree content is a *strict prefix* of the HEAD blob (deletion-only
  diff, worktree byte count < HEAD byte count). Check with
  ``git show HEAD:<f>`` vs the worktree read — if ``HEAD.startswith
  (worktree.rstrip())``, it's the gremlin.

- **Un-stick a phantom-truncated file:** ``git show HEAD:<file> >
  <file>`` — a full rewrite with identical content syncs both sides
  and clears the bogus ``git status`` entry. Only safe once the
  strict-prefix check confirms the file equals HEAD.

- **Reliable test-mirror workflow.** Build a sandbox-native mirror
  with ``git archive HEAD | tar -x -C <mirror>`` — gremlin-free by
  construction. Edit + test there. For files already edited
  Windows-side via the ``Edit`` tool, restore the pristine copy into
  the mirror from ``git archive`` then re-apply the edits with a
  Python ``str.replace`` script that asserts each anchor matches
  *exactly once* — a transcription slip fails loudly instead of
  silently corrupting. Sync the verified mirror back to the working
  tree with ``cp`` (a full-file write, which syncs both sides); ``cp``
  *from* a stale mount path just propagates the corruption, so the
  direction matters.

- **`cp` direction matters.** ``cp mirror→worktree`` works (writing a
  good file through the mount syncs it). ``cp worktree→mirror`` is
  unreliable (reading a possibly-stale file). Always copy *out of* the
  trustworthy source.

- **The offline test env.** ``.wheelhouse/linux-cp310`` lacks
  ``exceptiongroup`` and ``tomli`` (pytest 9's py<3.11 deps) and PyPI
  is firewalled. Minimal shims for both live in the session's
  ``outputs/shims/`` — ``exceptiongroup`` is a faithful-enough
  ``BaseExceptionGroup``/``ExceptionGroup`` backport, ``tomli``
  re-exports ``pip._vendor.tomli``. Put that dir on ``PYTHONPATH``
  alongside ``src`` and pytest 9.0.3 from the wheelhouse runs clean.

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
