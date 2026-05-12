"""Command-line entry point.

Top-level commands intended for routine use:

* ``obelisk extract <patch>``                — extract+emit a patch dump.
* ``obelisk diff <old_label> <new_label>`` — diff two extracts.
* ``obelisk render-unit <patch> <id>``       — render one unit's wikitext to stdout.

Diagnostics:

* ``obelisk inspect <patch>``                — counts/factions/coverage.
* ``obelisk extract-l10n <patch>``           — l10n corpus stats.
* ``obelisk ownership-report <patch>``       — SID-ownership coverage.
* ``obelisk goose <patch>``                  — Golden Goose Egg loot table.
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

from obelisk.emit import (
    emit_artifact_page,
    emit_astrologist_event_page,
    emit_attack_passive_page,
    emit_buildings_group_page,
    emit_difficulty_page,
    emit_entry_page,
    emit_entry_page_from_seed,
    emit_faction_page,
    emit_hero_class_page,
    emit_hero_page,
    emit_hero_specialization_page,
    emit_hero_sub_class_page,
    emit_item_set_page,
    emit_law_page,
    emit_map_object_page,
    emit_orphan_sub_skills_page,
    emit_skill_page,
    emit_spell_page,
    emit_unit_page,
    iter_entry_seeds,
    with_import_category,
)
from obelisk.extract import (
    CorePaths,
    extract_artifacts,
    extract_astrologist_events,
    extract_buildings,
    extract_difficulties,
    extract_factions,
    extract_hero_specializations,
    extract_hero_sub_classes,
    extract_heroes,
    extract_item_sets,
    extract_laws,
    extract_map_objects,
    extract_resources,
    extract_skills,
    extract_spells,
    extract_units_enriched,
    load_localization_corpus,
)

app = typer.Typer(
    add_completion=False,
    help="obelisk-bot - Olden Era wiki data pipeline",
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
        data/factions/<id>.wiki.txt        rendered Data:Faction/<id> page
                                            ({{Faction}} + {{Translation}}
                                             + 20 inline city-name Entry rows)
        data/hero_classes/<id>.wiki.txt    rendered Data:HeroClass/<id> page
                                            (12 derived class records)
        data/heroes/<id>.wiki.txt          rendered Data:Hero/<id> page
                                            ({{Hero}} + 2 {{Translation}} rows
                                             + N HeroStart{Squad,Skill,Magic} rows)
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
    from obelisk.extract.loader import load_json
    from obelisk.extract._pattern_passive_map import ATTACK_PASSIVES
    from obelisk.match import write_audit
    from obelisk.resolve import build_resolver

    final_label = label or patch.name
    target = out_root / final_label
    data_dir = target / "data"
    unit_dir = data_dir / "units"
    faction_dir = data_dir / "factions"
    hero_class_dir = data_dir / "hero_classes"
    hero_dir = data_dir / "heroes"
    hero_spec_dir = data_dir / "hero_specializations"
    hero_sub_class_dir = data_dir / "hero_sub_classes"
    spell_dir = data_dir / "spells"
    artifact_dir = data_dir / "artifacts"
    item_set_dir = data_dir / "item_sets"
    law_dir = data_dir / "laws"
    building_dir = data_dir / "buildings"
    map_object_dir = data_dir / "map_objects"
    skill_dir = data_dir / "skills"
    astrologist_event_dir = data_dir / "astrologist_events"
    difficulty_dir = data_dir / "difficulties"
    attack_passive_dir = data_dir / "attack_passives"
    for d in (unit_dir, faction_dir, hero_class_dir, hero_dir, hero_spec_dir,
              hero_sub_class_dir, spell_dir, artifact_dir, item_set_dir,
              law_dir, building_dir, map_object_dir, skill_dir,
              astrologist_event_dir, difficulty_dir, attack_passive_dir):
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
    n_unit_abilities_by_type: dict[str, int] = {}
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
        (unit_dir / f"{u.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        for ab in u.unit_abilities:
            n_unit_abilities_by_type[ab.ability_type] = (
                n_unit_abilities_by_type.get(ab.ability_type, 0) + 1
            )

    # Faction laws extracted up front so the Faction page emit can
    # inline this faction's {{FactionLawTier}} + {{LawTreePosition}}
    # rows. See D-033.
    law_result = extract_laws(paths)

    # Factions (Data:Faction/<id>). Each page carries {{Faction}} +
    # {{Translation | type=faction | …}} + 20 inline
    # {{Entry | type=FactionCityName | …}} rows + 5 {{FactionLawTier}}
    # + N {{LawTreePosition}} rows. See D-025 / D-026 / D-033.
    factions = extract_factions(paths)
    n_factions = 0
    n_city_names = 0
    for f in factions:
        page = emit_faction_page(
            f, corpus, resolver=resolver,
            law_tiers=law_result.faction_tiers,
            law_positions=law_result.tree_positions,
        )
        (faction_dir / f"{f.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_factions += 1
        n_city_names += len(f.city_names)
        total_chars += len(page)

    # Heroes + HeroClasses. 12 derived class records + ~177 per-hero
    # records. Hero rows sparse-emit fields that match the class
    # default (faction heroes uniformly inherit; campaign/tutorial
    # routinely override stats/start_level/atb). See D-027.
    hero_result = extract_heroes(paths)
    n_hero_classes = 0
    for hc in hero_result.hero_classes:
        page = emit_hero_class_page(hc, corpus, resolver=resolver)
        (hero_class_dir / f"{hc.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_hero_classes += 1
        total_chars += len(page)
    n_heroes = 0
    for h in hero_result.heroes:
        page = emit_hero_page(h, corpus, resolver=resolver)
        (hero_dir / f"{h.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_heroes += 1
        total_chars += len(page)

    # Hero specializations (Data:HeroSpecialization/<id>). 126 records,
    # each with N inline {{HeroSpecializationBonus}} rows. See D-028.
    spec_result = extract_hero_specializations(paths)
    n_hero_specs = 0
    n_spec_bonuses = 0
    for spec in spec_result.specializations:
        page = emit_hero_specialization_page(spec, corpus, resolver=resolver)
        (hero_spec_dir / f"{spec.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_hero_specs += 1
        n_spec_bonuses += len(spec.bonuses)
        total_chars += len(page)

    # Hero sub-classes (Data:HeroSubClass/<id>). 24 prestige classes,
    # 4 per faction × 6. Each carries 5 inline activation thresholds
    # plus N {{HeroSubClassBonus}} rows. See D-029.
    sub_class_result = extract_hero_sub_classes(paths)
    n_hero_sub_classes = 0
    n_sub_class_bonuses = 0
    for sub in sub_class_result.sub_classes:
        page = emit_hero_sub_class_page(sub, corpus, resolver=resolver)
        (hero_sub_class_dir / f"{sub.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_hero_sub_classes += 1
        n_sub_class_bonuses += len(sub.bonuses)
        total_chars += len(page)

    # Spells (Data:Spell/<id>). 137 records (battle + world + special +
    # test). Each carries 4 inline {{SpellRank}} rows. SP-dependent
    # placeholders intentionally remain unsubstituted. See D-030.
    spell_result = extract_spells(paths)
    n_spells = 0
    n_spell_ranks = 0
    for sp in spell_result.spells:
        page = emit_spell_page(sp, corpus, resolver=resolver)
        (spell_dir / f"{sp.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_spells += 1
        n_spell_ranks += len(sp.ranks)
        total_chars += len(page)

    # Artifacts (Data:Artifact/<id>). 304 records across 13 source
    # slot files. Each carries N inline {{Bonus | parent_type=artifact
    # | …}} rows. Artifact sets deferred. See D-031.
    artifact_result = extract_artifacts(paths)
    n_artifacts = 0
    n_artifact_bonuses = 0
    for art in artifact_result.artifacts:
        page = emit_artifact_page(art, corpus, resolver=resolver)
        (artifact_dir / f"{art.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_artifacts += 1
        n_artifact_bonuses += len(art.bonuses)
        total_chars += len(page)

    # Item sets (Data:ItemSet/<id>). 24 records, each with 1-3 tiers.
    # Per-tier bonuses flow into the unified Bonus table with
    # parent_type='item_set_tier'. See D-032.
    item_set_result = extract_item_sets(paths)
    n_item_sets = 0
    n_item_set_tiers = 0
    n_item_set_bonuses = 0
    for st in item_set_result.item_sets:
        page = emit_item_set_page(st, corpus, resolver=resolver)
        (item_set_dir / f"{st.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_item_sets += 1
        n_item_set_tiers += len(st.tiers)
        n_item_set_bonuses += sum(len(t.bonuses) for t in st.tiers)
        total_chars += len(page)

    # Faction laws (Data:Law/<id>). 198 production + 34 test laws,
    # 1-3 levels each. Per-level bonuses flow into the unified Bonus
    # table with parent_type='law_level'. LawTreePosition + FactionLawTier
    # rows are emitted on the parent Faction page. See D-033.
    n_laws = 0
    n_law_levels = 0
    n_law_bonuses = 0
    for law in law_result.laws:
        page = emit_law_page(law, corpus, resolver=resolver)
        (law_dir / f"{law.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_laws += 1
        n_law_levels += len(law.levels)
        n_law_bonuses += sum(len(lv.bonuses) for lv in law.levels)
        total_chars += len(page)
    n_law_positions = len(law_result.tree_positions)
    n_law_tiers = len(law_result.faction_tiers)

    # City buildings. 206 Cargo rows total (flattened per faction + sid
    # + level), but consolidated onto fewer pages per D-034 (revised):
    #   * All `category='hires'` rows for a faction → one page
    #     `<faction>_Build_creature_dwellings.wiki.txt`.
    #   * Every other building → one page per (faction, sid),
    #     e.g. `demon_Build_Main.wiki.txt` carrying all 3 levels.
    # Most category-specific extras (rollChances, optionalEffectsPerLevel,
    # market trade rates, etc.) are deliberately not extracted.
    building_result = extract_buildings(paths)
    n_buildings = len(building_result.buildings)
    n_building_by_cat: dict[str, int] = {}
    # Bucket key → list of BuildingRecord rows for that page.
    building_buckets: dict[str, list] = {}
    for b in building_result.buildings:
        n_building_by_cat[b.category] = n_building_by_cat.get(b.category, 0) + 1
        if b.category == "hires":
            page_id = f"{b.faction}_Build_creature_dwellings"
        else:
            page_id = f"{b.faction}_{b.sid}"
        building_buckets.setdefault(page_id, []).append(b)
    n_building_pages = 0
    for page_id, rows in building_buckets.items():
        page = emit_buildings_group_page(rows, corpus, resolver=resolver)
        (building_dir / f"{page_id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_building_pages += 1
        total_chars += len(page)

    # Adventure-map structures (Data:MapObject/<id>). ~118 rows across
    # ~22 source folders under DB/objects_logic/. Generic per D-035 —
    # captures display fields, universal scalars, guard_units, plus
    # a few sparse high-signal category-specific scalars. Rich payloads
    # (chest variants, hire unitsData, mine bonuses, etc.) deferred.
    map_object_result = extract_map_objects(paths)
    n_map_objects = 0
    n_map_object_by_cat: dict[str, int] = {}
    for mo in map_object_result.map_objects:
        page = emit_map_object_page(mo, corpus, resolver=resolver)
        (map_object_dir / f"{mo.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_map_objects += 1
        n_map_object_by_cat[mo.category] = n_map_object_by_cat.get(mo.category, 0) + 1
        total_chars += len(page)

    # Hero skills + sub-skills (Data:Skill/<skill_id>). 102 skills (30
    # production + 12 pseudo + 30 arena + 30 campaign), each with 1-3
    # levels. 617 sub-skills total (203+203+203+8). Each skill page
    # carries its top-level SkillDef row + per-level SkillLevelDef +
    # per-level EntryDef translation (type='skill_level') + Bonus rows,
    # and inlines every sub-skill referenced by any of this skill's
    # levels (SubSkillDef + TranslationDef type=sub_skill + Bonus
    # parent_type=sub_skill rows). Orphan sub-skills (8 test entries +
    # arena legacy *_old) emit onto the catch-all
    # Data:Skill/_orphan_sub_skills page. See D-037.
    skill_result = extract_skills(paths)
    n_skills = len(skill_result.skills)
    n_skill_levels = sum(len(s.levels) for s in skill_result.skills)
    n_skill_level_bonuses = sum(
        len(lv.bonuses) for s in skill_result.skills for lv in s.levels
    )
    n_sub_skills = len(skill_result.sub_skills)
    n_sub_skill_bonuses = sum(len(ss.bonuses) for ss in skill_result.sub_skills)
    # Bucket sub-skills by parent_skill_id so we can inline them on the
    # parent skill page; orphans collected separately for the catch-all.
    sub_skills_by_parent: dict[str, list] = {}
    orphan_sub_skills: list = []
    for ss in skill_result.sub_skills:
        if ss.parent_skill_id is None:
            orphan_sub_skills.append(ss)
        else:
            sub_skills_by_parent.setdefault(ss.parent_skill_id, []).append(ss)
    n_skill_pages = 0
    for skill in skill_result.skills:
        attached = sub_skills_by_parent.get(skill.id, ())
        page = emit_skill_page(skill, attached, corpus, resolver=resolver)
        (skill_dir / f"{skill.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_skill_pages += 1
        total_chars += len(page)
    n_orphan_sub_skills = len(orphan_sub_skills)
    if orphan_sub_skills:
        orphan_page = emit_orphan_sub_skills_page(
            orphan_sub_skills, corpus, resolver=resolver,
        )
        (skill_dir / "_orphan_sub_skills.wiki.txt").write_text(
            with_import_category(orphan_page), encoding="utf-8",
        )
        n_skill_pages += 1
        total_chars += len(orphan_page)

    # Astrologist weeks + months (Data:AstrologistEvent/<id>). 26 rows
    # total (15 weeks + 11 months) — the periodically-rolled global
    # modifiers ("Week of Sorcery", "Month of the Locust"). Identity
    # pulled from DB/weeks/{weeks,months}.json; per-event roll_chance
    # + global count_to_return from DB/weeks_info.json. See D-038.
    astrologist_event_result = extract_astrologist_events(paths)
    n_astrologist_events = 0
    n_astro_by_category: dict[str, int] = {}
    for ev in astrologist_event_result.events:
        page = emit_astrologist_event_page(ev, corpus, resolver=resolver)
        (astrologist_event_dir / f"{ev.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_astrologist_events += 1
        n_astro_by_category[ev.category] = n_astro_by_category.get(ev.category, 0) + 1
        total_chars += len(page)

    # Game difficulties (Data:Difficulty/<id>). 5 rows from
    # DB/difficulties.json (Easy/Normal/Hard/Expert/Impossible),
    # each carrying per-side starting-resource buckets and the
    # neutralPowerMultiplier scalar. The two sibling lobby files
    # ship empty configs in 2026-05-05 — extracted but yield 0 rows.
    # See D-039.
    difficulty_result = extract_difficulties(paths)
    n_difficulties = 0
    for diff in difficulty_result.difficulties:
        page = emit_difficulty_page(diff)
        (difficulty_dir / f"{diff.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_difficulties += 1
        total_chars += len(page)

    # Shared (hand-curated) Entry seed pages. Per-type top-level dirs
    # (data/<type>/); wiki pages land at Data:<PascalType>/<subtype>.
    # Cargo rows all write to the unified Entry table.
    n_entries_by_type: dict[str, int] = {}
    for entry_type, subtype in iter_entry_seeds():
        type_dir = data_dir / entry_type
        type_dir.mkdir(parents=True, exist_ok=True)
        seed_page = emit_entry_page_from_seed(entry_type, subtype, corpus, resolver=resolver)
        (type_dir / f"{subtype}.wiki.txt").write_text(with_import_category(seed_page), encoding="utf-8")
        n_entries_by_type[entry_type] = n_entries_by_type.get(entry_type, 0) + 1
        total_chars += len(seed_page)

    # Per-patch resource catalog (Data:Resource/<id>) — extracted from
    # DB/res/resources_info.json. Same Entry shape as the seeds, just
    # with provenance pointing at the source JSON. See D-036.
    resource_dir = data_dir / "resource"
    resource_dir.mkdir(parents=True, exist_ok=True)
    for r in extract_resources(paths):
        page = emit_entry_page(
            entry_type="resource",
            subtype=r.id,
            name_sid=r.name_sid,
            desc_sid=r.desc_sid,
            corpus=corpus,
            resolver=resolver,
            icon=r.icon,
            narrative_desc_sid=r.narrative_desc_sid,
            source_path=r.source_path,
        )
        (resource_dir / f"{r.id}.wiki.txt").write_text(with_import_category(page), encoding="utf-8")
        n_entries_by_type["resource"] = n_entries_by_type.get("resource", 0) + 1
        total_chars += len(page)

    n_entries = sum(n_entries_by_type.values())

    # Shared AttackPassive seed pages (Data:AttackPassive/<passive_id>).
    n_passives = 0
    for passive_id, info in ATTACK_PASSIVES.items():
        seed_page = emit_attack_passive_page(passive_id, info, corpus, resolver=resolver)
        (attack_passive_dir / f"{passive_id}.wiki.txt").write_text(with_import_category(seed_page), encoding="utf-8")
        n_passives += 1
        total_chars += len(seed_page)

    if result.audit_report is not None:
        write_audit(result.audit_report, target / "audit.json")

    # Coverage / association diagnostic pages — wiki-formatted tables
    # listing each emitted Data: page next to its expected top-level
    # article. Lands at out/<label>/diagnostic/. See emit/coverage.py.
    from obelisk.emit.coverage import (
        CoverageRow,
        render_coverage_pages,
    )
    from obelisk.emit import ENTRY_SEEDS
    # Coverage page lands at the top-level extract dir alongside _meta.json
    # — it's a single-file diagnostic, doesn't merit a sub-folder.
    coverage_dir = target
    # Build entry-seed coverage rows directly from ENTRY_SEEDS so we
    # carry the seed's name_sid through to the article-name resolver.
    _entry_seed_namespace = {
        "attack_archetype": "AttackArchetype",
        "movement": "Movement",
        "creature_type": "CreatureType",
        "hero_stat": "HeroStat",
        "unit_stat": "UnitStat",
    }
    entry_seed_rows: list[CoverageRow] = []
    for entry_type, subtypes in ENTRY_SEEDS.items():
        ns = _entry_seed_namespace.get(entry_type, entry_type)
        for subtype, seed in subtypes.items():
            from obelisk.emit.unit import _lookup_text as _lt
            sid = seed.get("name_sid")
            article = ""
            if isinstance(sid, str):
                article = _lt(sid, "english", corpus, resolver, None) or ""
            if not article:
                article = seed.get("display_name_fallback", "") or ""
            entry_seed_rows.append(CoverageRow(
                data_page=f"Data:{ns}/{subtype}",
                article=article,
                note=f"seed: {entry_type}",
            ))
    # Per-patch resource catalog already gets full Data:Resource/<id>
    # pages from extract_resources(); pass that record list directly
    # so the coverage table picks up resource names from L10n.
    _resources_for_coverage = list(extract_resources(paths))
    render_coverage_pages(
        coverage_dir,
        corpus=corpus,
        resolver=resolver,
        units=result.units,
        factions=factions,
        hero_classes=hero_result.hero_classes,
        heroes=hero_result.heroes,
        hero_specializations=spec_result.specializations,
        hero_sub_classes=sub_class_result.sub_classes,
        spells=spell_result.spells,
        artifacts=artifact_result.artifacts,
        item_sets=item_set_result.item_sets,
        laws=law_result.laws,
        buildings=building_result.buildings,
        map_objects=map_object_result.map_objects,
        skills=skill_result.skills,
        sub_skills=skill_result.sub_skills,
        astrologist_events=astrologist_event_result.events,
        difficulties=difficulty_result.difficulties,
        resources=_resources_for_coverage,
        entry_seed_rows=entry_seed_rows,
        attack_passive_ids=ATTACK_PASSIVES.keys(),
    )

    # Per-namespace index pages. One ``_index.wiki.txt`` per
    # data/<type>/ subdir, listing every member with a blurb from
    # docs/index_blurbs.md at the top. Wiki title for each lands at
    # the bare namespace (e.g. Data:Unit) — see
    # ``wiki_title_for_relpath`` for the special-case mapping. Run
    # after every per-entity emit so it picks up every file actually
    # written.
    from obelisk.diff import DIR_TO_WIKI_TABLE
    from obelisk.emit import load_index_blurbs, write_index_pages
    _index_blurbs_path = Path(__file__).resolve().parents[2] / "docs" / "index_blurbs.md"
    _blurbs = load_index_blurbs(_index_blurbs_path)
    n_index_pages_by_table = write_index_pages(
        data_dir, dir_to_table=DIR_TO_WIKI_TABLE, blurbs=_blurbs,
    )

    _write_meta(target, patch, len(result.units))

    elapsed = time.monotonic() - t3

    # Compose unit-ability sub-readout: passives, actives, auras, etc.
    # Order short-list by count desc for at-a-glance scan.
    ab_parts = ", ".join(
        f"{n} {kind.replace('_', ' ')}s"
        for kind, n in sorted(n_unit_abilities_by_type.items(),
                              key=lambda kv: -kv[1])
    ) or "no abilities"
    # Per-type entry-seed sub-readout (movement, creature_type, attack_archetype).
    seed_parts = ", ".join(
        f"{n} {t.replace('_', ' ')}"
        for t, n in sorted(n_entries_by_type.items())
    ) or "—"
    # Building sub-readout: dwellings (the `hires` category) called out
    # separately, everything else lumped into "other"; plus consolidated
    # page count (rows live on fewer pages per (faction, sid) bucketing).
    n_dwellings = n_building_by_cat.get("hires", 0)
    n_other = sum(n for cat, n in n_building_by_cat.items() if cat != "hires")
    bld_parts = f"{n_dwellings} dwellings, {n_other} other; {n_building_pages} pages"

    # MapObject sub-readout: highlight the meatier categories, lump the rest.
    _NOTABLE_MAP_CATS = ("hires", "portals", "res", "res_mines", "magic_mines", "chests", "event_banks")
    _notable_counts = [(c, n_map_object_by_cat.get(c, 0)) for c in _NOTABLE_MAP_CATS if n_map_object_by_cat.get(c)]
    _notable_total = sum(n for _, n in _notable_counts)
    _other_total = sum(n for c, n in n_map_object_by_cat.items() if c not in _NOTABLE_MAP_CATS)
    _parts = [f"{n} {c.replace('_', ' ')}" for c, n in _notable_counts]
    if _other_total:
        _parts.append(f"{_other_total} other")
    map_obj_parts = ", ".join(_parts) or "—"

    console.print(
        f"[green]Wrote in {elapsed:.1f}s -> {target} ({total_chars:,} chars):[/green]\n"
        f"  {n_factions} factions ({n_city_names} city-name entries)\n"
        f"  {n_laws} laws ({n_law_levels} levels, {n_law_bonuses} bonus rows; "
        f"{n_law_positions} tree positions, {n_law_tiers} faction-tier rows)\n"
        f"  {n_buildings} buildings ({bld_parts})\n"
        f"  {n_map_objects} map objects ({map_obj_parts})\n"
        f"  {n_artifacts} artifacts ({n_artifact_bonuses} bonus rows)\n"
        f"  {n_item_sets} item sets ({n_item_set_tiers} tiers, {n_item_set_bonuses} bonus rows)\n"
        f"  {len(result.units)} units ({ab_parts})\n"
        f"  {n_passives} attack-passive seeds\n"
        f"  {n_hero_classes} hero classes\n"
        f"  {n_hero_sub_classes} hero sub-classes ({n_sub_class_bonuses} bonus rows)\n"
        f"  {n_heroes} heroes\n"
        f"  {n_hero_specs} hero specializations ({n_spec_bonuses} bonus rows)\n"
        f"  {n_spells} spells ({n_spell_ranks} rank rows)\n"
        f"  {n_skills} skills ({n_skill_levels} levels, {n_skill_level_bonuses} bonus rows; "
        f"{n_sub_skills} sub-skills [{n_orphan_sub_skills} orphan], {n_sub_skill_bonuses} sub-skill bonus rows; "
        f"{n_skill_pages} pages)\n"
        f"  {n_astrologist_events} astrologist events "
        f"({n_astro_by_category.get('week', 0)} weeks, {n_astro_by_category.get('month', 0)} months)\n"
        f"  {n_difficulties} difficulties\n"
        f"  {n_entries} curated entry seeds ({seed_parts})\n"
        f"  {len(n_index_pages_by_table)} index pages "
        f"({sum(n_index_pages_by_table.values())} member links)"
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
    ``obelisk extract <patch>`` first to produce each side.

    Writes to ``<out_root>/<new_label>/diff_vs_<old_label>/``::

        changed_pages/<id>.diff   per-page unified diff (drilldown, local-only)
        wiki_summary.md           operator markdown summary
        patch_article.wiki.txt    body for Data:Patches/<new_label>
        manifest.json             upload manifest (consumed by ``obelisk upload``)
        complete.diff             deep core-JSON diff, excluding Lang/
        localization.diff         deep core-JSON diff for Lang/ only

    Run ``obelisk upload <old> <new>`` afterward to push.
    """
    from obelisk.diff import (
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
            f"run 'obelisk extract' for the previous patch first"
        )
        raise typer.Exit(1)
    if not new_dir.is_dir():
        console.print(
            f"[red]No extract at {new_dir}[/red] - "
            f"run 'obelisk extract' for the new patch first"
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

    # Patch article — bot-managed wiki page, tag with the standard
    # import category like every other data page so wiki-side audits
    # treat it the same way.
    article = render_patch_article(wd, new_label)
    (diff_dir / "patch_article.wiki.txt").write_text(
        with_import_category(article), encoding="utf-8",
    )

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

    # Manifest: what `obelisk upload` should push. Shape matches
    # obelisk.upload.manifest.Manifest — ``kind="diff"`` + patch
    # article + every changed page. ``label``/``old_label`` are also
    # left in legacy positions (``new_label``) for backward compat with
    # manifests written before kind/label were standardized.
    manifest = {
        "kind": "diff",
        "label": new_label,
        "old_label": old_label,
        "new_label": new_label,  # legacy alias, kept for any tooling still reading it
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
        f"[cyan]obelisk upload {old_label} {new_label}[/cyan]"
    )


# ----------------------------------------------------------------------------
# generate (full-push manifest)
# ----------------------------------------------------------------------------


@app.command("generate")
def cmd_generate(
    label: str = typer.Argument(..., help="Label of the extracted patch to manifest."),
    out_root: Path = typer.Option(
        Path("out"), "--out", help="Output root. Default: out/"
    ),
    include_coverage: bool = typer.Option(
        True, "--coverage/--no-coverage",
        help="Include coverage.wiki.txt as Data:Coverage (default on).",
    ),
) -> None:
    """Generate a full-push manifest for an extracted patch.

    Walks ``out/<label>/data/`` (and optionally the top-level
    ``coverage.wiki.txt``) and writes ``out/<label>/manifest.json``
    listing every page as status='added'. No patch article.

    Use this for initial wiki population or any "push everything"
    scenario. ``obelisk upload <label>`` (single arg) consumes it.

    Overwrites any existing ``out/<label>/manifest.json``.
    """
    from obelisk.upload import build_full_manifest

    extract_dir = out_root / label
    if not extract_dir.is_dir():
        console.print(
            f"[red]No extract at {extract_dir}[/red] - "
            f"run 'obelisk extract' first"
        )
        raise typer.Exit(1)

    manifest = build_full_manifest(
        extract_dir, label=label, include_coverage=include_coverage,
    )
    manifest_path = extract_dir / "manifest.json"
    manifest.write(manifest_path)

    console.print(
        f"[green]Wrote {len(manifest.pages)} entries[/green] -> {manifest_path}"
    )
    if include_coverage:
        # Lightweight confirmation so an operator can tell at a glance whether
        # the coverage page actually got picked up (it's optional in extract).
        cov_present = any(e.title == "Data:Coverage" for e in manifest.pages)
        if cov_present:
            console.print("  Data:Coverage included")
        else:
            console.print(
                "  [yellow]Data:Coverage requested but coverage.wiki.txt not found[/yellow]"
            )
    console.print(
        f"[bold]Next:[/bold] [cyan]obelisk upload {label}[/cyan] "
        f"(use --dry-run first for a preview)"
    )


# ----------------------------------------------------------------------------
# upload
# ----------------------------------------------------------------------------


def _log_result(log_fp, title: str, status: str, detail: str) -> None:
    """Append one JSON line per result to the .jsonl log."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "title": title,
        "status": status,
    }
    if detail:
        entry["detail"] = detail
    log_fp.write(json.dumps(entry) + "\n")
    log_fp.flush()


def _run_upload(
    manifest_path: Path,
    body_root: Path,
    config_path: Path,
    *,
    dry_run: bool,
) -> None:
    """Shared upload loop. Reads the manifest, drives the client, logs.

    ``body_root`` is the extract dir — relpaths in the manifest's
    ``pages`` are resolved against it. The patch article's path (if
    present) is resolved against the manifest's *containing* dir, which
    is where ``obelisk diff`` writes ``patch_article.wiki.txt``.

    Per-run logs land next to the manifest:

    * ``upload_log.jsonl`` — one JSON object per result (real runs).
    * ``upload_log.dryrun.jsonl`` — one JSON object per manifest entry
      (dry runs; status mirrors the manifest, no wiki contact).
    * ``upload_errors.txt`` — failures only, written if any (real runs).
    """
    if not manifest_path.is_file():
        console.print(f"[red]No manifest at {manifest_path}[/red]")
        raise typer.Exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_dir = manifest_path.parent
    pages = manifest.get("pages") or []
    patch_article = manifest.get("patch_article")

    if dry_run:
        console.print("[yellow]DRY RUN[/yellow] - showing what would be pushed:")
        # Persist the same info to a parallel log file so operators have a
        # grep-able record without having to actually push. Status values
        # mirror the manifest verbatim (added/changed/removed) — we can't
        # predict written vs unchanged without contacting the wiki, so
        # don't pretend to. Filename is .dryrun. to keep it side-by-side
        # with real-run logs without ever clobbering them.
        dryrun_log = manifest_dir / "upload_log.dryrun.jsonl"
        with dryrun_log.open("w", encoding="utf-8") as log_fp:
            for entry in pages:
                console.print(f"  {entry.get('status', '?'):8s} {entry['title']}")
                _log_result(
                    log_fp,
                    entry["title"],
                    entry.get("status", "added"),
                    "",
                )
            if patch_article:
                console.print(f"  article  {patch_article['title']}")
                _log_result(
                    log_fp,
                    patch_article["title"],
                    "patch_article",
                    "",
                )
        console.print(f"[bold]Total:[/bold] {len(pages)} pages"
                      + (" + 1 patch article" if patch_article else ""))
        console.print(f"  log: {dryrun_log}")
        return

    from obelisk.upload import WikiClient, load_config

    cfg = load_config(config_path)
    client = WikiClient(cfg)
    console.print(
        f"[bold]Wiki:[/bold] {cfg.scheme}://{cfg.host}{cfg.path}  "
        f"(throttle: {cfg.requests_per_second} req/s, maxlag: {cfg.maxlag}s)"
    )

    pushed = unchanged = failed = skipped = 0
    failure_lines: list[str] = []

    log_path = manifest_dir / "upload_log.jsonl"
    # Overwrite the log each run — rerunning the same manifest is
    # routine (idempotent), and a stale "I succeeded last time" line
    # confuses postmortems. Failure file is rewritten too.
    with log_path.open("w", encoding="utf-8") as log_fp:
        for entry in pages:
            title = entry["title"]
            relpath = entry["relpath"]
            status = entry.get("status", "added")
            if status == "removed":
                # We never auto-delete on the wiki side — log+skip.
                _log_result(log_fp, title, "skipped_removed", "manifest status=removed")
                console.print(
                    f"[yellow]skip removed:[/yellow] {title} (not auto-deleting on wiki)"
                )
                skipped += 1
                continue
            body_path = body_root / relpath
            if not body_path.is_file():
                detail = f"missing body file: {body_path}"
                _log_result(log_fp, title, "failed", detail)
                failure_lines.append(f"{title}\t{detail}")
                console.print(f"  [red]MISSING[/red] {title}: {body_path}")
                failed += 1
                continue
            body = body_path.read_text(encoding="utf-8")
            result_up = client.put_page(title, body)
            _log_result(log_fp, title, result_up.status, result_up.detail)
            if result_up.status == "written":
                pushed += 1
                console.print(f"  [green]pushed[/green] {title}")
            elif result_up.status == "unchanged":
                unchanged += 1
                # Don't spam — unchanged is the common case on reruns.
            else:
                failed += 1
                failure_lines.append(f"{title}\t{result_up.detail}")
                console.print(f"  [red]FAILED[/red] {title}: {result_up.detail}")

        # Patch article (diff manifests only).
        if patch_article:
            art_title = patch_article["title"]
            art_path = manifest_dir / patch_article["path"]
            if not art_path.is_file():
                detail = f"missing patch article: {art_path}"
                _log_result(log_fp, art_title, "failed", detail)
                failure_lines.append(f"{art_title}\t{detail}")
                console.print(f"[red]MISSING patch article: {art_path}[/red]")
                failed += 1
            else:
                art_body = art_path.read_text(encoding="utf-8")
                art_result = client.put_page(art_title, art_body)
                _log_result(log_fp, art_title, art_result.status, art_result.detail)
                if art_result.status == "written":
                    console.print(f"[green]pushed[/green] {art_title}")
                    pushed += 1
                elif art_result.status == "unchanged":
                    console.print(f"[grey]unchanged[/grey] {art_title}")
                    unchanged += 1
                else:
                    console.print(f"[red]FAILED[/red] {art_title}: {art_result.detail}")
                    failure_lines.append(f"{art_title}\t{art_result.detail}")
                    failed += 1

    err_path = manifest_dir / "upload_errors.txt"
    if failure_lines:
        err_path.write_text(
            "# Failures from upload run at "
            f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
            "# title<TAB>detail\n"
            + "\n".join(failure_lines)
            + "\n",
            encoding="utf-8",
        )
    elif err_path.exists():
        # No failures this run — remove a stale error file from a prior run.
        err_path.unlink()

    console.print(
        f"[bold]Upload:[/bold] {pushed} written, {unchanged} unchanged, "
        f"{skipped} skipped, {failed} failed"
    )
    console.print(f"  log: {log_path}")
    if failure_lines:
        console.print(f"  [red]errors:[/red] {err_path}")


@app.command("upload")
def cmd_upload(
    label_a: str = typer.Argument(..., help=(
        "Label to upload. With one arg: full-push from out/<label>/manifest.json. "
        "With two args: diff-push (label_a=old, label_b=new)."
    )),
    label_b: str | None = typer.Argument(
        None, help="If provided, upload the diff from label_a (old) -> label_b (new)."
    ),
    out_root: Path = typer.Option(
        Path("out"), "--out", help="Output root. Default: out/"
    ),
    config_path: Path = typer.Option(
        Path("obelisk.ini"), "--config", help="Wiki credentials."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print what would be pushed without contacting the wiki."
    ),
) -> None:
    """Push pages to the wiki.

    Two modes:

    * **Full push** (one arg): ``obelisk upload <label>`` reads
      ``out/<label>/manifest.json`` (produced by ``obelisk generate``)
      and pushes every listed page. Used for initial wiki population
      or any full re-sync.

    * **Diff push** (two args): ``obelisk upload <old> <new>`` reads
      ``out/<new>/diff_vs_<old>/manifest.json`` (produced by
      ``obelisk diff``) and pushes the changed pages plus the patch
      article. Used in the routine patch cycle.

    Both modes are idempotent — pages whose on-wiki text already
    matches are skipped. Throttling honors the
    ``requests_per_second`` and ``maxlag`` settings in ``obelisk.ini``.

    Per-run logs (``upload_log.jsonl`` + ``upload_errors.txt`` on
    failure) are written next to the manifest.
    """
    if label_b is None:
        # Full-push mode.
        extract_dir = out_root / label_a
        manifest_path = extract_dir / "manifest.json"
        if not manifest_path.is_file():
            console.print(
                f"[red]No manifest at {manifest_path}[/red] - "
                f"run 'obelisk generate {label_a}' first"
            )
            raise typer.Exit(1)
        body_root = extract_dir
    else:
        # Diff-push mode. label_a is old, label_b is new.
        old_label, new_label = label_a, label_b
        new_dir = out_root / new_label
        diff_dir = new_dir / f"diff_vs_{old_label}"
        manifest_path = diff_dir / "manifest.json"
        if not manifest_path.is_file():
            console.print(
                f"[red]No manifest at {manifest_path}[/red] - "
                f"run 'obelisk diff {old_label} {new_label}' first"
            )
            raise typer.Exit(1)
        body_root = new_dir

    _run_upload(manifest_path, body_root, config_path, dry_run=dry_run)


# ----------------------------------------------------------------------------
# render-unit (single-unit preview)
# ----------------------------------------------------------------------------


@app.command("render-unit")
def cmd_render_unit(
    patch: Path = typer.Argument(..., help="Path to a patch dump."),
    unit_id: str = typer.Argument(..., help="Unit id to render."),
) -> None:
    """Render one unit's wikitext to stdout. Diagnostic / preview tool."""
    from obelisk.extract.loader import load_json
    from obelisk.resolve import build_resolver

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
    from obelisk.extract import assign_ownership, extract_units

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


@app.command("goose")
def cmd_goose(
    patch: Path = typer.Argument(..., help="Path to a patch dump (parent of Core/)."),
    out_root: Path = typer.Option(
        Path("out"), "--out", help="Output root. Default: out/"
    ),
    label: str | None = typer.Option(
        None, "--label", help="Override the derived label (default: patch dir name)."
    ),
    out_file: Path | None = typer.Option(
        None, "--out-file", "-o",
        help="Specific output file path. Overrides --out / --label.",
    ),
) -> None:
    """Render the Golden Goose Egg loot table to a wiki-formatted file.

    Reads ``DB/reward_golden_egg.json`` and emits a sortable wikitable
    with Weight / Rate / Reward columns. Default output location lands
    alongside the rest of the patch's extract artifacts at
    ``<out_root>/<label>/golden_egg.wiki.txt``; pass ``--out-file`` to
    drop it somewhere specific instead. Drop the result onto the wiki
    article for the artifact and copy-paste through.
    """
    from obelisk.emit.golden_egg import load_golden_egg, render_golden_egg_table

    paths = CorePaths.from_root(patch)
    egg_path = paths.db / "reward_golden_egg.json"
    if not egg_path.is_file():
        console.print(f"[red]No reward_golden_egg.json at {egg_path}[/red]")
        raise typer.Exit(1)

    corpus = load_localization_corpus(paths, languages={"english"})
    doc = load_golden_egg(egg_path)
    page = render_golden_egg_table(doc, corpus)

    if out_file is not None:
        out_path = out_file
    else:
        final_label = label or patch.name
        target_dir = out_root / final_label
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / "golden_egg.wiki.txt"
    out_path.write_text(with_import_category(page), encoding="utf-8")
    n_rows = len(doc.get("array") or [])
    console.print(
        f"[green]Wrote {n_rows} reward rows to {out_path}[/green]"
    )


if __name__ == "__main__":
    app()
