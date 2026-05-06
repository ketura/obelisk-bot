# obelisk-bot

Heroes of Might and Magic: Olden Era — wiki data pipeline.

Extracts game JSON from `Core.zip`, normalizes it into canonical records, emits Cargo stub articles for MediaWiki, diffs against prior releases, and uploads changes via the MediaWiki API.

The wiki ([oldenera.wiki.gg](https://oldenera.wiki.gg/)) is the consumer. This project's deliverable is the **shared context** — the structured data layer. Display articles, infobox templates, and prose are out of scope and live on the wiki side.

## Status

Pre-alpha. The Unit category is end-to-end: extract → emit → patch-cycle diff with optional upload. Placeholder resolution covers ~97.5% of `{N}` substitutions across 16 languages. Other categories (Heroes, Spells, Items, Buildings, Faction Laws, etc.) are inventoried in [`docs/widget_inventory.md`](docs/widget_inventory.md) and follow once Units stabilize.

## Architecture

See [`docs/decisions.md`](docs/decisions.md) for the locked architectural decisions.
See [`docs/widget_inventory.md`](docs/widget_inventory.md) for the standing list of entities to extract.

## Patch cycle

When a new patch drops:

```sh
# 1. Unzip the new Core.zip into a dated folder
#    e.g. ../2026-04-30/Core/...

# 2. Extract the new patch (and the old one, if you don't have it yet).
#    Output: out/<label>/  (label defaults to the dir name)
obelisk extract ../2026-03-15
obelisk extract ../2026-04-30

# 3. Diff the two by label. Output: out/<new>/diff_vs_<old>/
#    Review wiki_summary.md, patch_article.wiki.txt, json_diff.txt.
#    Hand-edit the patch article if you want.
obelisk diff 2026-03-15 2026-04-30

# 4. Push when satisfied.
obelisk upload 2026-03-15 2026-04-30
```

`diff` finds both extracts under `out/`. The `_meta.json` written by `extract` records the source patch path, so the deep core-JSON diff works automatically as long as both source patch dirs are still on disk.

`upload` reads `manifest.json` from the diff folder and pushes each listed page plus the patch article. Idempotent — pages whose on-wiki text already matches are skipped. Pass `--dry-run` to preview the push list without contacting the wiki. Hand-edits to `patch_article.wiki.txt` made between diff and upload are picked up.

## All commands

```sh
# Top-level (routine use)
obelisk extract <patch>                       # extract+emit a patch dump
obelisk diff <old_label> <new_label>    # diff two extracts (writes manifest.json)
obelisk upload <old_label> <new_label>        # push the manifest's pages to the wiki

# Diagnostics
obelisk render-unit <patch> <unit_id>         # render one unit's wikitext to stdout
obelisk inspect <patch>                       # counts/factions/coverage
obelisk extract-l10n <patch>                  # l10n corpus stats
obelisk ownership-report <patch>              # SID-ownership coverage
```

All path/label arguments are positional. Optional `--out <root>` overrides the output root (defaults to `out/`).

## Output layout

```
out/
  <label>/                         one folder per extracted patch
    Data/
      Unit/<id>.wiki.txt           rendered wiki page
      Unit/<id>.json               source JSON copy
    audit.json                     logic-vs-views audit report
    _meta.json                     source patch path + timestamps
    diff_vs_<other_label>/         diffs live under the newer extract
      changed_pages/<id>.diff      per-page unified diff
      wiki_summary.md              operator markdown summary
      patch_article.wiki.txt       body for Data:Patches/<label>  (hand-editable)
      manifest.json                upload manifest (consumed by `obelisk upload`)
      json_diff.txt                deep core-JSON diff (when both _meta point at live patch dirs)
```

## Wiki credentials

Upload mode reads `obelisk.ini` from the project root (gitignored). Copy `obelisk.ini.example` and fill in your bot account + bot password. MediaWiki bot passwords are managed at `Special:BotPasswords` on the wiki.

## Install

```sh
uv venv
uv pip install -e ".[dev]"
```

The CLI is installed as `obelisk` (and is also runnable via `python -m obelisk.cli`).

## License

Apache 2.0. See [`LICENSE`](LICENSE).

The game data itself is © Unfrozen / Ubisoft and is not redistributed by this project — users supply their own `Core.zip` from a legal copy of the game.
