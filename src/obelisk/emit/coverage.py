"""Coverage / association diagnostic pages.

After the main extract+emit run, this module produces a set of
wiki-formatted pages that list every emitted ``Data:`` page next
to the top-level article that's expected to reference it. The
purpose is operator diagnostics: published to the wiki, the
*Article* column's redlinks make the gap of "data exists but no
top-level article yet" immediately visible, so we can decide
whether autogenerating stubs is worth the trouble.

Output is a single file at ``out/<label>/coverage.wiki.txt`` —
one sortable table per category, all in one document.

The single-file layout exists because the user copy-pastes the
whole document onto a single wiki page for at-a-glance review.

Article-name strategy: use the resolved English name verbatim
(e.g. ``Bathym, Duke of Jewels``). No automatic disambiguators —
collisions are surfaced through the redlink mechanism on the wiki
itself, and the user picks a disambig convention as a follow-up.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from obelisk.emit.unit import _lookup_text
from obelisk.models.localization import LocalizationCorpus
from obelisk.resolve import PlaceholderResolver


@dataclass(frozen=True)
class CoverageRow:
    """One entry in a coverage table."""

    data_page: str           # full ``Data:Foo/bar`` title
    article: str             # resolved English display name; "" if unknown
    note: str = ""           # optional inline note (e.g. "synthetic id")


# Smart-quote → ASCII map applied to article display strings before
# wrapping them as wiki links. Wiki article titles want stable ASCII so
# redlink resolution doesn't depend on which Unicode variant the source
# happens to use; the original quoted form survives in the data page
# itself (Data:Hero/<id>'s name field), this only affects the
# ``[[Title]]`` link target the coverage table generates.
_SMART_QUOTE_TR = str.maketrans({
    "‘": "'",  # left single
    "’": "'",  # right single (most common — possessive forms)
    "‚": "'",  # single low-9
    "‛": "'",  # single high-reversed-9
    "“": '"',  # left double
    "”": '"',  # right double
    "„": '"',  # double low-9
    "‟": '"',  # double high-reversed-9
    "′": "'",  # prime
    "″": '"',  # double prime
})


def _normalize_quotes(text: str) -> str:
    return text.translate(_SMART_QUOTE_TR)


def _resolve_name(
    name_sid: str | None,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> str:
    """Return the resolved English text for an SID, or "" if missing.

    Smart quotes are normalized to ASCII so wiki article-title matching
    is stable (e.g. ``Beelzebub's Hand`` / ``Beelzebub’s Hand`` collapse to
    the same target)."""
    if not name_sid:
        return ""
    text = _lookup_text(name_sid, "english", corpus, resolver, None)
    if not text:
        return ""
    return _normalize_quotes(text)


def _wiki_link_data(title: str) -> str:
    """Render a ``Data:`` page link. Backticks render as code-style on
    most MediaWiki skins, helping these stand out from article links."""
    return f"[[{title}]]"


def _wiki_link_article(name: str) -> str:
    """Render an article link, or empty when no candidate name is known.

    Returning a literal empty cell keeps the redlink mechanism honest:
    populated cells link to articles that may or may not exist (so
    they go red if missing); empty cells signal "we don't even know
    what the article should be called."
    """
    if not name:
        return ""
    return f"[[{name}]]"


def _make_table(
    rows: Iterable[CoverageRow],
    link_counts: dict[str, int],
) -> str:
    """Render a sortable wikitable.

    Columns: Link Count / Article / Data Page / Notes. Link Count is
    the number of data pages (across *all* categories) whose article
    candidate equals this row's article — sortable so collisions
    bubble to the top. Empty when the article cell is empty (nothing
    to count)."""
    out: list[str] = [
        '{| class="wikitable sortable"',
        "! Link Count !! Article !! Data Page !! Notes",
    ]
    for row in rows:
        data_link = _wiki_link_data(row.data_page)
        article_link = _wiki_link_article(row.article)
        count_cell = str(link_counts.get(row.article, 0)) if row.article else ""
        out.append(f"|-")
        out.append(f"| {count_cell} || {article_link} || {data_link} || {row.note}")
    out.append("|}")
    return "\n".join(out)


def _make_combined_page(
    by_category: dict[str, list[CoverageRow]],
) -> str:
    """Render a single document with one section per category.

    Layout: top-level summary table (Category / Total / With Article /
    Coverage %), then one ``== Category ==`` section per category
    carrying that category's sortable Link Count / Article / Data Page
    / Notes table. Designed to be pasted onto a single wiki page so
    the user can scan all categories at once.

    Link Count is computed once across the union of all categories'
    rows so duplicates show up regardless of whether they live in the
    same category (typical: campaign + production hero variants
    sharing a name) or cross-category (rare but possible).
    """
    # Global per-article reference count.
    from collections import Counter
    link_counts: Counter[str] = Counter()
    for rows in by_category.values():
        for r in rows:
            if r.article:
                link_counts[r.article] += 1

    out: list[str] = []
    out.append("= Data Page Coverage =")
    out.append("")
    out.append(
        "Each section lists every ``Data:`` page emitted by the latest "
        "extract paired with the top-level article that's expected to "
        "reference it. Redlinks in the *Article* column indicate top-level "
        "articles that don't yet exist; the *Link Count* column shows how "
        "many data pages (across all categories) share each article — sort "
        "descending to find collisions."
    )
    out.append("")

    # Summary table.
    out.append('{| class="wikitable sortable"')
    out.append("! Category !! Total !! With Article !! Coverage")
    for category, rows in sorted(by_category.items()):
        total = len(rows)
        with_article = sum(1 for r in rows if r.article)
        pct = (with_article / total * 100) if total else 0
        out.append("|-")
        out.append(
            f"| [[#{category}|{category}]] || {total} || {with_article} || {pct:.0f}%"
        )
    out.append("|}")
    out.append("")

    # Per-category tables.
    for category, rows in sorted(by_category.items()):
        rows_sorted = sorted(rows, key=lambda r: r.data_page)
        n_total = len(rows_sorted)
        n_with = sum(1 for r in rows_sorted if r.article)
        n_without = n_total - n_with
        out.append(f"== {category} ==")
        out.append("")
        out.append(
            f"; Total: {n_total}  &mdash;  with article candidate: "
            f"{n_with}  &mdash;  without: {n_without}"
        )
        out.append("")
        out.append(_make_table(rows_sorted, link_counts))
        out.append("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Per-entity-type adapters: turn record lists into coverage rows.
# Each adapter takes (records, corpus, resolver) and returns list[CoverageRow].
# ---------------------------------------------------------------------------


def _rows_for_simple_named(
    records: Iterable[Any],
    *,
    namespace: str,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
    note_fn=lambda r: "",
) -> list[CoverageRow]:
    """Generic adapter for records with ``id`` and ``name_sid`` fields.

    Each row maps ``Data:<namespace>/<id>`` to the resolved English
    name. ``note_fn(record)`` produces an optional per-row note."""
    out: list[CoverageRow] = []
    for r in records:
        rid = getattr(r, "id", None)
        if not isinstance(rid, str):
            continue
        name = _resolve_name(getattr(r, "name_sid", None), corpus, resolver)
        out.append(CoverageRow(
            data_page=f"Data:{namespace}/{rid}",
            article=name,
            note=note_fn(r),
        ))
    return out


def _rows_for_buildings(
    buildings: Iterable[Any],
    *,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> list[CoverageRow]:
    """Building pages are bucketed by (faction, sid) — the dwellings
    bucket is a per-faction megapage, others are per-(faction, sid).
    Article candidates: blank for the dwellings bucket (no clear
    single article), and the resolved name of the L1 record for
    everything else."""
    by_page: dict[str, list[Any]] = {}
    for b in buildings:
        if getattr(b, "category", None) == "hires":
            page_id = f"{b.faction}_Build_creature_dwellings"
        else:
            page_id = f"{b.faction}_{b.sid}"
        by_page.setdefault(page_id, []).append(b)
    out: list[CoverageRow] = []
    for page_id, rows in sorted(by_page.items()):
        if page_id.endswith("_Build_creature_dwellings"):
            out.append(CoverageRow(
                data_page=f"Data:Building/{page_id}",
                article="",
                note="dwelling megapage; no single article",
            ))
            continue
        # First (lowest-level) row's name is the natural article candidate.
        first = sorted(rows, key=lambda b: getattr(b, "level", 0))[0]
        name = _resolve_name(getattr(first, "name_sid", None), corpus, resolver)
        out.append(CoverageRow(
            data_page=f"Data:Building/{page_id}",
            article=name,
            note=f"{len(rows)} level(s)" if len(rows) > 1 else "",
        ))
    return out


def _rows_for_skills(
    skills: Iterable[Any],
    sub_skills: Iterable[Any],
    *,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
) -> list[CoverageRow]:
    """One row per top-level skill page; sub-skills are inlined on
    the parent and don't get their own coverage row. Plus one row
    for the catch-all orphan sub-skills page when present."""
    out: list[CoverageRow] = []
    for s in skills:
        rid = getattr(s, "id", None)
        if not isinstance(rid, str):
            continue
        variant = getattr(s, "variant", "")
        name = _resolve_name(getattr(s, "name_sid", None), corpus, resolver)
        out.append(CoverageRow(
            data_page=f"Data:Skill/{rid}",
            article=name,
            note=variant if variant != "production" else "",
        ))
    has_orphans = any(
        getattr(ss, "parent_skill_id", None) is None for ss in sub_skills
    )
    if has_orphans:
        out.append(CoverageRow(
            data_page="Data:Skill/_orphan_sub_skills",
            article="",
            note="catch-all for unreferenced sub-skills",
        ))
    return out


def _rows_for_difficulties(
    difficulties: Iterable[Any],
) -> list[CoverageRow]:
    """Difficulties have no L10n names — the id (Easy/Normal/…) is
    the canonical display string."""
    out: list[CoverageRow] = []
    for d in difficulties:
        rid = getattr(d, "id", None)
        if not isinstance(rid, str):
            continue
        out.append(CoverageRow(
            data_page=f"Data:Difficulty/{rid}",
            article=rid,
            note="",
        ))
    return out


def _rows_for_entry_seeds(
    entry_seed_pairs: Iterable[tuple[str, str]],
    namespace_by_type: dict[str, str],
    *,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
    sid_resolver_for_seed,
) -> list[CoverageRow]:
    """Hand-curated Entry seed pages (movement / creature_type / …).

    ``namespace_by_type`` maps the on-disk type to the wiki-side
    namespace (e.g. ``movement`` → ``Movement``).
    ``sid_resolver_for_seed`` is a callable
    ``(entry_type, subtype) -> name_sid`` that returns the SID
    used for that seed's display name."""
    out: list[CoverageRow] = []
    for entry_type, subtype in entry_seed_pairs:
        ns = namespace_by_type.get(entry_type, entry_type)
        name_sid = sid_resolver_for_seed(entry_type, subtype)
        name = _resolve_name(name_sid, corpus, resolver) if name_sid else ""
        out.append(CoverageRow(
            data_page=f"Data:{ns}/{subtype}",
            article=name,
            note=f"seed: {entry_type}",
        ))
    return out


def render_coverage_pages(
    diagnostic_dir: Path,
    *,
    corpus: LocalizationCorpus,
    resolver: PlaceholderResolver | None,
    units: Iterable[Any] = (),
    factions: Iterable[Any] = (),
    hero_classes: Iterable[Any] = (),
    heroes: Iterable[Any] = (),
    hero_specializations: Iterable[Any] = (),
    hero_sub_classes: Iterable[Any] = (),
    spells: Iterable[Any] = (),
    artifacts: Iterable[Any] = (),
    item_sets: Iterable[Any] = (),
    laws: Iterable[Any] = (),
    buildings: Iterable[Any] = (),
    map_objects: Iterable[Any] = (),
    skills: Iterable[Any] = (),
    sub_skills: Iterable[Any] = (),
    astrologist_events: Iterable[Any] = (),
    difficulties: Iterable[Any] = (),
    resources: Iterable[Any] = (),
    entry_seed_rows: Iterable[CoverageRow] = (),
    attack_passive_ids: Iterable[str] = (),
) -> list[Path]:
    """Render coverage tables to ``diagnostic_dir``. Returns the list of
    files written. Each callable parameter corresponds to one extract
    result — pass the existing record collection (no need to convert)."""
    diagnostic_dir.mkdir(parents=True, exist_ok=True)

    # Resolve every source's rows.
    by_category: dict[str, list[CoverageRow]] = {}

    def add(category: str, rows: list[CoverageRow]) -> None:
        if rows:
            by_category[category] = rows

    add("Unit", _rows_for_simple_named(
        units, namespace="Unit", corpus=corpus, resolver=resolver,
    ))
    add("Faction", _rows_for_simple_named(
        factions, namespace="Faction", corpus=corpus, resolver=resolver,
    ))
    add("HeroClass", _rows_for_simple_named(
        hero_classes, namespace="HeroClass", corpus=corpus, resolver=resolver,
    ))
    add("Hero", _rows_for_simple_named(
        heroes, namespace="Hero", corpus=corpus, resolver=resolver,
    ))
    add("HeroSpecialization", _rows_for_simple_named(
        hero_specializations, namespace="HeroSpecialization",
        corpus=corpus, resolver=resolver,
    ))
    add("HeroSubClass", _rows_for_simple_named(
        hero_sub_classes, namespace="HeroSubClass",
        corpus=corpus, resolver=resolver,
    ))
    add("Spell", _rows_for_simple_named(
        spells, namespace="Spell", corpus=corpus, resolver=resolver,
    ))
    add("Artifact", _rows_for_simple_named(
        artifacts, namespace="Artifact", corpus=corpus, resolver=resolver,
    ))
    add("ItemSet", _rows_for_simple_named(
        item_sets, namespace="ItemSet", corpus=corpus, resolver=resolver,
    ))
    add("Law", _rows_for_simple_named(
        laws, namespace="Law", corpus=corpus, resolver=resolver,
    ))
    add("Building", _rows_for_buildings(
        buildings, corpus=corpus, resolver=resolver,
    ))
    add("MapObject", _rows_for_simple_named(
        map_objects, namespace="MapObject", corpus=corpus, resolver=resolver,
        note_fn=lambda r: getattr(r, "category", "") or "",
    ))
    add("Skill", _rows_for_skills(
        skills, sub_skills, corpus=corpus, resolver=resolver,
    ))
    add("AstrologistEvent", _rows_for_simple_named(
        astrologist_events, namespace="AstrologistEvent",
        corpus=corpus, resolver=resolver,
        note_fn=lambda r: getattr(r, "category", "") or "",
    ))
    add("Difficulty", _rows_for_difficulties(difficulties))
    add("Resource", _rows_for_simple_named(
        resources, namespace="Resource", corpus=corpus, resolver=resolver,
    ))

    # Entry seeds the caller already collected.
    seed_rows = list(entry_seed_rows)
    if seed_rows:
        by_category["EntrySeed"] = seed_rows

    # Attack passives — id-only, no L10n display name handy here.
    ap_rows = [
        CoverageRow(
            data_page=f"Data:AttackPassive/{pid}",
            article="",
            note="seed",
        )
        for pid in attack_passive_ids
    ]
    if ap_rows:
        by_category["AttackPassive"] = ap_rows

    # Write a single combined document — one summary table + one
    # sortable per-category table per section. The user copy-pastes
    # the whole file onto a single wiki page for at-a-glance review.
    # Tagged with the standard import category like every other
    # bot-emitted data page.
    from obelisk.emit import with_import_category
    page = _make_combined_page(by_category)
    fp = diagnostic_dir / "coverage.wiki.txt"
    fp.write_text(with_import_category(page), encoding="utf-8")
    return [fp]
