"""Command-line entry point.

Top-level commands intended for routine use:

* ``artificer extract <patch>``                — extract+emit a patch dump.
* ``artificer diff <old_label> <new_label>`` — diff two extracts.
* ``artificer render-unit <patch> <id>``       — render one unit's wikitext to stdout.

Diagnostics:

* ``artificer inspect <patch>``                — counts/factions/coverage.
* ``artificer extract-l10n <patch>``           — l10n corpus stats.
* ``artificer ownership-report <patch>``       — SID-ownership coverage.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from artificer.emit import (
    emit_attack_passive_page,
    emit_entry_page_from_seed,
    emit_faction_page,
    emit_unit_page,
    iter_entry_seeds,
)
from artificer.extract import (
    CorePaths,
    extract_factions,
    extract_units_enriched,
    load_localization_corpus,
)

app = typer.Typer(
    add_completion=False,
    help="artificer-bot - Olden Era wiki data pipeline",
    no_args_is_help=True,
)

console = Console()


# ----------------------------------------------------------------------------
# Cycle metadata helpers
# ----------------------------------------------------------------------------


def _write_meta(target_dir: Path, source_patch: Path, n_units: int) -> None:
    """Persist the source-patch path so diff can find core JSON later."""
    meta = {
        "source_patch": str(source_patch.resolve()),
        "label": target_dir.name,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "n_units": n_units,
    }
    (target_dir / "_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )


def _read_meta(extract_dir: Path) -> dict | None:
    fp = extract_dir / "_meta.json"
    if not fp.is_file():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None


# ----------------------------------------------------------------------------
# extract
# ----------------------------------------------------------------------------


@app.command("extract")
def cmd_extract(
    patch: Path = typer.Argument(..., help="Path to a patch dump (parent of Core/)."),
    out_root: Path = typer.Option(
        Path("out"), "--out", help="Output root. Default: out/"
    ),
    label: str | None = typer.Option(
        None, "--label", help="Override the derived label (default: patch dir name)."
    ),
) -> None:
    """Extract canonical records from a patch dump and emit wikitext.

    Writes to ``<out_root>/<label>/``::

        data/units/<id>.wiki.txt           rendered Data:Unit/<id> wiki page
                                            (includes the unit's
                                            {{UnitAttack | …}} invocation)
        data/units/<id>.json               source JSON copy
        data/factions/<id>.wiki.txt        rendered Data:Faction/<id> page
                                            ({{Faction}} + {{Translation}}
                                             + 20 inline city-name Entry rows)
        data/<type>/<subtype>.wiki.txt     shared Data:<PascalType>/<subtype>
                                            (per-type top-level dirs:
                                            attack_archetype/, movement/,
                                            creature_type/, ...; rows live
                                            in the unified Cargo Entry table)
        data/attack_passives/<id>.wiki.txt shared Data:AttackPassive/<id> seed
        audit.json                         logic-vs-views audit report
        _meta.json                         source patch path + timestamps

    Currently emits Units, Factions (+ city-name Entry rows), shared
    Entry seeds (attack archetypes, movement types, creature types),
    and AttackPassive seeds. Other categories will be added in place;
    no further CLI changes required.
    """
    from artificer.extract.loader import load_json
    from artificer.extract._pattern_passive_map import ATTACK_PASSIVES
    from artificer.match import write_audit
    from artificer.resolve import build_resolver

    final_label = label or patch.name
    target = out_root / final_label
    data_dir = target / "data"
    unit_dir = data_dir / "units"
    faction_dir = data_dir / "factions"
    attack_passive_dir = data_dir / "attack_passives"
    for d in (unit_dir, faction_dir, attack_passive_dir):
        d.mkdir(parents=True, exist_ok=True)
    # Per-type Entry dirs (data/<type>/) get created lazily inside the
    # entry loop below so the seed dict drives the directory layout.

    paths = CorePaths.from_root(patch)

    t0 = time.monotonic()
    result = extract_units_enriched(paths)
    console.print(
        f"[bold]Extracted {len(result.units)} units[/bold] in {time.monotonic()-t0:.1f}s"
    )

    t1 = time.monotonic()
    corpus = load_localization_corpus(paths)
    console.print(
        f"[bold]L10n corpus loaded[/bold] in {time.monotonic()-t1:.1f}s "
        f"({len(corpus.entries):,} entries)"
    )

    t2 = time.monotonic()
    resolver = build_resolver(paths.core_root, corpus=corpus)
    console.print(f"[bold]Resolver built[/bold] in {time.monotonic()-t2:.1f}s")

    t3 = time.monotonic()
    total_chars = 0
    for u in result.units:
        src = paths.core_root / u.source_path
        unit_json = None
        if src.is_file():
            doc = load_json(src)
            if isinstance(doc, dict):
                unit_json = next(
                    (
                        e
                        for e in (doc.get("array") or [])
                        if isinstance(e, dict) and e.get("id") == u.id
                    ),
                    None,
                )
        page = emit_unit_page(u, None, corpus, resolver=resolver, unit_json=unit_json)
        total_chars += len(page)
        (unit_dir / f"{u.id}.wiki.txt").write_text(page, encoding="utf-8")
        if src.is_file():
            (unit_dir / f"{u.id}.json").write_bytes(src.read_bytes())

    # Factions (Data:Faction/<id>). Each page carries {{Faction}} +
    # {{Translation | type=faction | …}} + 20 inline
    # {{Entry | type=FactionCityName | …}} rows for the city-name
    # pool. See D-025 / D-026.
    factions = extract_factions(paths)
    n_factions = 0
    n_city_names = 0
    for f in factions:
        page = emit_faction_page(f, corpus, resolver=resolver)
        (faction_dir / f"{f.id}.wiki.txt").write_text(page, encoding="utf-8")
        n_factions += 1
        n_city_names += len(f.city_names)
        total_chars += len(page)

    # Shared (hand-curated) Entry seed pages. Per-type top-level dirs
    # (data/<type>/); wiki pages land at Data:<PascalType>/<subtype>.
    # Cargo rows all write to the unified Entry table.
    n_entries = 0
    for entry_type, subtype in iter_entry_seeds():
        type_dir = data_dir / entry_type
        type_dir.mkdir(parents=True, exist_ok=True)
        seed_page = emit_entry_page_from_seed(entry_type, subtype, corpus, resolver=resolver)
        (type_dir / f"{subtype}.wiki.txt").write_text(seed_page, encoding="utf-8")
        n_entries += 1
        total_chars += len(seed_page)

    # Shared AttackPassive seed pages (Data:AttackPassive/<passive_id>).
    n_passives = 0
    for passive_id, info in ATTACK_PASSIVES.items():
        seed_page = emit_attack_passive_page(passive_id, info, corpus, resolver=resolver)
        (attack_passive_dir / f"{passive_id}.wiki.txt").write_text(seed_page, encoding="utf-8")
        n_passives += 1
        total_chars += len(seed_page)

    if result.audit_report is not None:
        write_audit(result.audit_report, target / "audit.json")

    _write_meta(target, patch, len(result.units))

    elapsed = time.monotonic() - t3
    console.print(
        f"[green]Wrote {len(result.units)} unit pages, "
        f"{n_factions} faction pages, {n_city_names} city-name entries, "
        f"{n_entries} curated entry seeds, {n_passives} attack-passive seeds[/green] "
        f"({total_chars:,} chars) in {elapsed:.1f}s -> {target}"
    )


# ----------------------------------------------------------------------------
# diff
# ----------------------------------------------------------------------------


@app.command("diff")
def cmd_diff_patch(
    old_label: str = typer.Argument(..., help="Label of the previous extracted patch."),
    new_label: str = typer.Argument(..., help="Label of the new extracted patch."),
    out_root: Path = typer.Option(
        Path("out"), "--out", help="Output root. Default: out/"
    ),
) -> None:
    """Diff two extracted patches by label.

    Both labels must already exist under ``<out_root>/``. Run
    ``artificer extract <patch>`` first to produce each side.

    Writes to ``<out_root>/<new_label>/diff_vs_<old_label>/``::

        changed_pages/<id>.diff   per-page unified diff (drilldown, local-only)
        wiki_summary.md           operator markdown summary
        patch_article.wiki.txt    body for Data:Patches/<new_label>
        manifest.json             upload manifest (consumed by ``artificer upload``)
        complete.diff             deep core-JSON diff, excluding Lang/
        localization.diff         deep core-JSON diff for Lang/ only

    Run ``artificer upload <old> <new>`` afterward to push.
    """
    from artificer.diff import (
        diff_emit_dirs,
        diff_core_dirs,
        render_patch_article,
        render_summary,
        render_unified_diff,
        split_lang_entries,
    )

    old_dir = out_root / old_label
    new_dir = out_root / new_label
    if not old_dir.is_dir():
        console.print(
            f"[red]No extract at {old_dir}[/red] - "
            f"run 'artificer extract' for the previous patch first"
        )
        raise typer.Exit(1)
    if not new_dir.is_dir():
        console.print(
            f"[red]No extract at {new_dir}[/red] - "
            f"run 'artificer extract' for the new patch first"
        )
        raise typer.Exit(1)

    diff_dir = new_dir / f"diff_vs_{old_label}"
    drilldown_dir = diff_dir / "changed_pages"
    drilldown_dir.mkdir(parents=True, exist_ok=True)

    # Wiki diff
    wd = diff_emit_dirs(old_dir, new_dir)
    console.print(
        f"[bold]Wiki diff:[/bold] {len(wd.changed)} changed, "
        f"{len(wd.added)} added, {len(wd.removed)} removed"
    )

    # Drilldown
    for page in wd.changed_pages:
        safe_name = page.page_id or Path(page.relpath).stem
        (drilldown_dir / f"{safe_name}.diff").write_text(
            page.diff_text, encoding="utf-8"
        )

    # Operator summary
    (diff_dir / "wiki_summary.md").write_text(
        render_summary(wd, new_label), encoding="utf-8"
    )

    # Patch article
    article = render_patch_article(wd, new_label)
    (diff_dir / "patch_article.wiki.txt").write_text(article, encoding="utf-8")

    # JSON diff if both metas exist + source patches still on disk.
    # Split into complete.diff (DB/ + everything non-Lang) and
    # localization.diff (Lang/ only) so reviewers can skim the meaty
    # changes without wading through translation churn.
    old_meta = _read_meta(old_dir)
    new_meta = _read_meta(new_dir)
    if old_meta and new_meta:
        old_src = Path(old_meta.get("source_patch", ""))
        new_src = Path(new_meta.get("source_patch", ""))
        if old_src.is_dir() and new_src.is_dir():
            t0 = time.monotonic()
            json_entries = diff_core_dirs(old_src, new_src)
            non_lang, lang = split_lang_entries(json_entries)
            (diff_dir / "complete.diff").write_text(
                render_unified_diff(non_lang), encoding="utf-8"
            )
            (diff_dir / "localization.diff").write_text(
                render_unified_diff(lang), encoding="utf-8"
            )
            console.print(
                f"[bold]JSON diff:[/bold] {len(non_lang)} entries -> complete.diff, "
                f"{len(lang)} entries -> localization.diff "
                f"({time.monotonic()-t0:.1f}s)"
            )
        else:
            console.print(
                "[yellow]Skipping JSON diff: source patch dir(s) not on disk[/yellow]"
            )
    else:
        console.print(
            "[yellow]Skipping JSON diff: missing _meta.json[/yellow]"
        )

    # Manifest: what `artificer upload` should push.
    manifest = {
        "old_label": old_label,
        "new_label": new_label,
        "patch_article": {
            "title": f"Data:Patches/{new_label}",
            "path": "patch_article.wiki.txt",
        },
        "pages": [
            {
                "title": p.wiki_title,
                "relpath": p.relpath,
                "status": p.status,
            }
            for p in wd.changed_pages
        ],
    }
    (diff_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    console.print(f"[green]Diff artifacts:[/green] {diff_dir}")
    console.print(
        f"[bold]Next:[/bold] review the artifacts, then run "
        f"[cyan]artificer upload {old_label} {new_label}[/cyan]"
    )


# ----------------------------------------------------------------------------
# upload
# ----------------------------------------------------------------------------


@app.command("upload")
def cmd_upload(
    old_label: str = typer.Argument(..., help="Label of the previous extracted patch."),
    new_label: str = typer.Argument(..., help="Label of the new extracted patch."),
    out_root: Path = typer.Option(
        Path("out"), "--out", help="Output root. Default: out/"
    ),
    config_path: Path = typer.Option(
        Path("artificer.ini"), "--config", help="Wiki credentials."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print what would be pushed without contacting the wiki."
    ),
) -> None:
    """Push the diff between two extracted patches to the wiki.

    Reads ``out/<new_label>/diff_vs_<old_label>/manifest.json`` (produced by
    ``artificer diff``) and uploads each listed page plus the patch
    article. Idempotent: pages whose on-wiki text already matches are skipped.

    The patch article body is read from disk, so any hand-edits to
    ``patch_article.wiki.txt`` after diff are picked up.
    """
    new_dir = out_root / new_label
    diff_dir = new_dir / f"diff_vs_{old_label}"
    manifest_path = diff_dir / "manifest.json"

    if not manifest_path.is_file():
        console.print(
            f"[red]No manifest at {manifest_path}[/red] - "
            f"run 'artificer diff {old_label} {new_label}' first"
        )
        raise typer.Exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if dry_run:
        console.print(f"[yellow]DRY RUN[/yellow] - showing what would be pushed:")
        for entry in manifest["pages"]:
            console.print(f"  {entry['status']:8s} {entry['title']}")
        art = manifest["patch_article"]
        console.print(f"  article  {art['title']}")
        return

    from artificer.upload import WikiClient, load_config

    cfg = load_config(config_path)
    client = WikiClient(cfg)
    pushed = unchanged = failed = skipped = 0

    for entry in manifest["pages"]:
        title = entry["title"]
        relpath = entry["relpath"]
        status = entry["status"]
        if status == "removed":
            console.print(
                f"[yellow]skip removed:[/yellow] {title} (not auto-deleting on wiki)"
            )
            skipped += 1
            continue
        body_path = new_dir / relpath
        if not body_path.is_file():
            console.print(f"  [red]MISSING[/red] {title}: {body_path}")
            failed += 1
            continue
        body = body_path.read_text(encoding="utf-8")
        result_up = client.put_page(title, body)
        if result_up.status == "written":
            pushed += 1
            console.print(f"  [green]pushed[/green] {title}")
        elif result_up.status == "unchanged":
            unchanged += 1
        else:
            failed += 1
            console.print(f"  [red]FAILED[/red] {title}: {result_up.detail}")

    art = manifest["patch_article"]
    art_title = art["title"]
    art_path = diff_dir / art["path"]
    if not art_path.is_file():
        console.print(f"[red]MISSING patch article: {art_path}[/red]")
        failed += 1
    else:
        art_body = art_path.read_text(encoding="utf-8")
        art_result = client.put_page(art_title, art_body)
        if art_result.status == "written":
            console.print(f"[green]pushed[/green] {art_title}")
            pushed += 1
        elif art_result.status == "unchanged":
            console.print(f"[grey]unchanged[/grey] {art_title}")
            unchanged += 1
        else:
            console.print(f"[red]FAILED[/red] {art_title}: {art_result.detail}")
            failed += 1

    console.print(
        f"[bold]Upload:[/bold] {pushed} written, {unchanged} unchanged, "
        f"{skipped} skipped, {failed} failed"
    )


# ----------------------------------------------------------------------------
# render-unit (single-unit preview)
# ----------------------------------------------------------------------------


@app.command("render-unit")
def cmd_render_unit(
    patch: Path = typer.Argument(..., help="Path to a patch dump."),
    unit_id: str = typer.Argument(..., help="Unit id to render."),
) -> None:
    """Render one unit's wikitext to stdout. Diagnostic / preview tool."""
    from artificer.extract.loader import load_json
    from artificer.resolve import build_resolver

    paths = CorePaths.from_root(patch)
    result = extract_units_enriched(paths)
    target = result.by_id.get(unit_id)
    if target is None:
        console.print(f"[red]No unit with id={unit_id!r}[/red]")
        raise typer.Exit(1)

    corpus = load_localization_corpus(paths)
    resolver = build_resolver(paths.core_root, corpus=corpus)
    src_json_path = paths.core_root / target.source_path
    unit_json = None
    if src_json_path.is_file():
        doc = load_json(src_json_path)
        if isinstance(doc, dict):
            arr = doc.get("array") or []
            unit_json = next(
                (e for e in arr if isinstance(e, dict) and e.get("id") == unit_id),
                None,
            )
    page = emit_unit_page(
        target, None, corpus, resolver=resolver, unit_json=unit_json
    )
    console.print(page)


# ----------------------------------------------------------------------------
# Diagnostics
# ----------------------------------------------------------------------------


@app.command("inspect")
def cmd_inspect(
    patch: Path = typer.Argument(..., help="Path to a patch dump."),
    show_unit: str | None = typer.Option(
        None, "--show", help="Print one unit's canonical record."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Sanity-check a patch dump: counts, factions, ability coverage."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    paths = CorePaths.from_root(patch)
    console.print(f"[bold]Core root:[/bold] {paths.core_root}")
    result = extract_units_enriched(paths)
    console.print(f"[bold green]Extracted {len(result.units)} units[/bold green]")
    if result.skipped:
        console.print(f"[yellow]Skipped {len(result.skipped)} files[/yellow]")
        for fp, reason in result.skipped[:5]:
            console.print(f"  {fp.name}: {reason}")
    if result.warnings:
        console.print(f"[yellow]{len(result.warnings)} warnings[/yellow]")
        for fp, msg in result.warnings[:5]:
            console.print(f"  {fp.name}: {msg}")

    table = Table(title="Units per faction")
    table.add_column("Faction")
    table.add_column("Count", justify="right")
    by_faction: dict[str, int] = {}
    for u in result.units:
        by_faction[u.faction.value] = by_faction.get(u.faction.value, 0) + 1
    for f, c in sorted(by_faction.items()):
        table.add_row(f, str(c))
    console.print(table)

    total_abilities = sum(len(u.unit_abilities) for u in result.units)
    units_with = sum(1 for u in result.units if u.unit_abilities)
    stat_passive_count = sum(
        1 for u in result.units for a in u.unit_abilities if a.ability_type == "stat_passive"
    )
    console.print(
        f"\n[bold]UnitAbility coverage:[/bold] {total_abilities} ability rows "
        f"across {units_with}/{len(result.units)} units "
        f"({stat_passive_count} synthesized as stat_passive)"
    )

    creature_counts: dict[str | None, int] = {}
    for u in result.units:
        creature_counts[u.creature_type] = creature_counts.get(u.creature_type, 0) + 1
    ct_table = Table(title="Creature type distribution")
    ct_table.add_column("Type")
    ct_table.add_column("Count", justify="right")
    for ct, n in sorted(creature_counts.items(), key=lambda x: -x[1]):
        ct_table.add_row(str(ct), str(n))
    console.print(ct_table)

    if show_unit:
        u = result.by_id.get(show_unit)
        if u is None:
            console.print(f"[red]No unit with id={show_unit!r}[/red]")
            raise typer.Exit(1)
        console.print(f"\n[bold]{u.id}[/bold] ({u.faction.value} tier {u.tier})")
        console.print(u.model_dump_json(indent=2))


@app.command("extract-l10n")
def cmd_extract_l10n(
    patch: Path = typer.Argument(..., help="Path to a patch dump."),
    languages: list[str] = typer.Option([], "--lang", "-l"),
) -> None:
    """L10n corpus row counts."""
    paths = CorePaths.from_root(patch)
    corpus = load_localization_corpus(paths, languages or None)
    console.print(f"[bold]Loaded {len(corpus.entries)} L10n entries[/bold]")
    by_lang: dict[str, int] = {}
    for (_sid, lang), _ in corpus.entries.items():
        by_lang[lang] = by_lang.get(lang, 0) + 1
    table = Table(title="L10n rows per language")
    table.add_column("Language")
    table.add_column("Rows", justify="right")
    for lang, c in sorted(by_lang.items()):
        table.add_row(lang, str(c))
    console.print(table)


@app.command("ownership-report")
def cmd_ownership_report(
    patch: Path = typer.Argument(..., help="Path to a patch dump."),
    show_orphans: bool = typer.Option(False, "--orphans"),
    limit: int = typer.Option(20, "--limit"),
) -> None:
    """SID-ownership coverage diagnostic."""
    from artificer.extract import assign_ownership, extract_units

    paths = CorePaths.from_root(patch)
    units = extract_units(paths).units
    corpus = load_localization_corpus(paths, languages={"english"})
    claims = assign_ownership(units=units, corpus=corpus)

    total_sids = len(corpus.all_sids())
    owned: set[str] = set()
    for c in claims.values():
        owned |= c.all_owned_sids
    orphans = corpus.all_sids() - owned

    console.print(f"[bold]Total English SIDs:[/bold] {total_sids}")
    console.print(f"[bold]Owned by a unit:[/bold] {len(owned)}")
    console.print(f"[bold]Orphan (not unit-owned):[/bold] {len(orphans)}")

    full_units = sum(1 for c in claims.values() if c.name_sid)
    with_narr = sum(1 for c in claims.values() if c.narrative_description_sid)
    with_slots = sum(1 for c in claims.values() if c.unit_abilities)
    console.print(
        f"\n[bold]Per-unit coverage:[/bold] "
        f"{full_units}/{len(units)} have name SID, "
        f"{with_narr}/{len(units)} have narrative description, "
        f"{with_slots}/{len(units)} have at least one discovered ability slot."
    )

    if show_orphans:
        console.print(f"\n[bold]First {limit} orphan SIDs:[/bold]")
        for sid in sorted(orphans)[:limit]:
            txt = corpus.get(sid, "english") or ""
            console.print(f"  {sid:50s} {txt[:60]!r}")


if __name__ == "__main__":
    app()
