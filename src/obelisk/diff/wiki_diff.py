"""Compare two emit-dir trees and produce per-page diffs.

An *emit dir* is the folder produced by ``emit-all-units`` (or eventually
the multi-entity emit), shaped like::

    emit_dir/
        Data/
            Unit/<id>.wiki.txt
            ...

This module walks both trees, classifies each page as added / removed /
changed / unchanged, computes a unified diff, and produces a summary.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path


# Maps the on-disk category directory under data/ to the actual wiki-side
# page-namespace name. The on-disk side uses snake_case (lowercase plural
# for collections, singular for shared-Entry domains) while the wiki side
# uses PascalCase (singular for Entry-domain pages, singular for Unit).
# Note: shared-Entry domains all *store* into the unified Cargo `Entry`
# table even though their pages live under per-domain namespaces
# (Data:Movement/<subtype>, Data:CreatureType/<subtype>, ...) — this map
# governs the page-name namespace, not the underlying Cargo table.
# Update when a new top-level data category comes online.
DIR_TO_WIKI_TABLE: dict[str, str] = {
    "units": "Unit",
    "attack_passives": "AttackPassive",
    "factions": "Faction",
    "hero_classes": "HeroClass",
    "heroes": "Hero",
    "hero_specializations": "HeroSpecialization",
    "hero_sub_classes": "HeroSubClass",
    "spells": "Spell",
    "artifacts": "Artifact",
    "item_sets": "ItemSet",
    "laws": "Law",
    "buildings": "Building",
    "map_objects": "MapObject",
    "skills": "Skill",
    "astrologist_events": "AstrologistEvent",
    "difficulties": "Difficulty",
    "attack_archetype": "AttackArchetype",
    "movement": "Movement",
    "creature_type": "CreatureType",
    "resource": "Resource",
    "hero_stat": "HeroStat",
    "unit_stat": "UnitStat",
}

# Back-compat alias for code that still uses the private name.
_DIR_TO_WIKI_TABLE = DIR_TO_WIKI_TABLE


def wiki_title_for_relpath(relpath: str) -> str:
    """Given a path relative to an extract dir (e.g.
    ``data/units/angel.wiki.txt``), return the on-wiki page title
    (``Data:Unit/angel``). Empty string if the path doesn't map.

    Special cases:

    * Top-level extract files (no ``data/`` prefix) are looked up
      against ``_ROOT_FILES_TO_TITLE`` — currently only
      ``coverage.wiki.txt`` -> ``Data:Coverage``.
    * ``data/<type>/_index.wiki.txt`` -> ``Data:<Table>`` (bare, no
      subpage). The index page is the namespace landing page.
    * ``cargo_templates/<X>.wiki.txt`` -> ``Template:<X>``. Cargo def
      docs land in the Template namespace so the wiki side resolves
      ``{{XDef | ...}}`` transclusions against them.
    """
    p = Path(relpath)
    parts = p.parts
    # Top-level (extract-root) artifact pages.
    if len(parts) == 1:
        return _ROOT_FILES_TO_TITLE.get(parts[0], "")
    # Cargo template docs -> Template namespace.
    if parts[0] == "cargo_templates" and len(parts) == 2:
        page_id = p.stem.replace(".wiki", "")
        return f"Template:{page_id}"
    if parts[0] not in ("data", "Data"):
        return ""
    if len(parts) < 2:
        return ""
    table = DIR_TO_WIKI_TABLE.get(parts[1], parts[1])
    page_id = p.stem.replace(".wiki", "")
    # The per-namespace index page lands at the bare Data:<Table>
    # title, not Data:<Table>/_index.
    if page_id == "_index":
        return f"Data:{table}"
    return f"Data:{table}/{page_id}"


# Top-level extract files (not under data/) that we want to upload.
# Coverage is bot-managed and useful as a wiki diagnostic. Goose lives
# at the repo root (not in extract output) and is intentionally not
# pushed. Extend as we add new top-level artifacts.
_ROOT_FILES_TO_TITLE: dict[str, str] = {
    "coverage.wiki.txt": "Data:Coverage",
}


@dataclass(frozen=True)
class WikiPageDiff:
    """One page's status between old and new emit dirs."""

    relpath: str  # relative to emit dir, e.g. "Data/Unit/crossbowman.wiki.txt"
    status: str   # one of: added | removed | changed | unchanged
    old_lines: int
    new_lines: int
    diff_text: str = ""  # unified diff (empty for unchanged)

    @property
    def line_delta(self) -> int:
        return self.new_lines - self.old_lines

    @property
    def insertions(self) -> int:
        """Lines starting with ``+`` in the diff hunks (excluding the ``+++`` header)."""
        n = 0
        for ln in self.diff_text.splitlines():
            if ln.startswith("+") and not ln.startswith("+++"):
                n += 1
        return n

    @property
    def deletions(self) -> int:
        """Lines starting with ``-`` in the diff hunks (excluding the ``---`` header)."""
        n = 0
        for ln in self.diff_text.splitlines():
            if ln.startswith("-") and not ln.startswith("---"):
                n += 1
        return n

    @property
    def hunk_summary(self) -> str:
        """Compact ``+N / -M`` rendering for human-readable summaries.

        For ``added``/``removed`` statuses, simplifies to a single ``+N`` or ``-M``.
        """
        if self.status == "unchanged":
            return ""
        ins = self.insertions
        dels = self.deletions
        if self.status == "added":
            return f"+{ins}"
        if self.status == "removed":
            return f"-{dels}"
        return f"+{ins} / -{dels}"

    @property
    def entity_type(self) -> str:
        """Derive the entity category (top-level data dir) from the path.

        ``data/units/foo.wiki.txt``           -> ``units``
        ``data/attack_passives/foo.wiki.txt`` -> ``attack_passives``
        ``data/movement/fly.wiki.txt``        -> ``movement``
        ``data/creature_type/undead.wiki.txt``-> ``creature_type``
        Otherwise: empty string.
        """
        parts = Path(self.relpath).parts
        if len(parts) >= 2 and parts[0] in ("data", "Data"):
            return parts[1]
        return ""

    @property
    def page_id(self) -> str:
        """The wiki page id without the ``.wiki.txt`` suffix.

        ``Data/Unit/crossbowman.wiki.txt`` -> ``crossbowman``
        ``data/movement/fly.wiki.txt``     -> ``fly``
        """
        return Path(self.relpath).stem.replace(".wiki", "")

    @property
    def wiki_title(self) -> str:
        """The full on-wiki page title, e.g. ``Data:Unit/crossbowman`` or
        ``Data:Movement/fly``.

        Joins the wiki-side table name (looked up from the on-disk
        directory) with the page id. The mapping lives in
        ``DIR_TO_WIKI_TABLE`` at module top.
        """
        return wiki_title_for_relpath(self.relpath)


@dataclass
class WikiDiff:
    """Aggregate diff over an entire emit-dir comparison."""

    pages: list[WikiPageDiff] = field(default_factory=list)

    @property
    def changed_pages(self) -> list[WikiPageDiff]:
        return [p for p in self.pages if p.status != "unchanged"]

    @property
    def added(self) -> list[WikiPageDiff]:
        return [p for p in self.pages if p.status == "added"]

    @property
    def removed(self) -> list[WikiPageDiff]:
        return [p for p in self.pages if p.status == "removed"]

    @property
    def changed(self) -> list[WikiPageDiff]:
        return [p for p in self.pages if p.status == "changed"]

    def by_entity_type(self) -> dict[str, list[WikiPageDiff]]:
        out: dict[str, list[WikiPageDiff]] = {}
        for p in self.changed_pages:
            out.setdefault(p.entity_type, []).append(p)
        return out


def _list_pages(emit_dir: Path) -> dict[str, Path]:
    """Map relpath -> absolute path for every ``.wiki.txt`` file under
    ``data/`` (or legacy ``Data/``).

    Restricting to the data root keeps diff artifacts (which may live in
    sibling subfolders inside the same emit dir) out of the comparison.
    """
    out: dict[str, Path] = {}
    for root_name in ("data", "Data"):
        data_dir = emit_dir / root_name
        if not data_dir.is_dir():
            continue
        for fp in data_dir.rglob("*.wiki.txt"):
            rel = fp.relative_to(emit_dir).as_posix()
            out[rel] = fp
    return out


def _read_lines(fp: Path) -> list[str]:
    try:
        return fp.read_text(encoding="utf-8").splitlines(keepends=False)
    except FileNotFoundError:
        return []


def _normalize_for_diff(lines: list[str]) -> list[str]:
    """Drop lines we don't want to flag as changes (the bot-managed banner)."""
    out = []
    for ln in lines:
        if ln.startswith("<!-- Bot-managed page."):
            continue
        out.append(ln)
    return out


def diff_emit_dirs(
    old_dir: Path,
    new_dir: Path,
    *,
    context_lines: int = 3,
) -> WikiDiff:
    """Walk both emit dirs and produce one WikiPageDiff per page."""
    old_pages = _list_pages(old_dir)
    new_pages = _list_pages(new_dir)
    all_paths = sorted(set(old_pages) | set(new_pages))

    diff = WikiDiff()
    for rel in all_paths:
        old_fp = old_pages.get(rel)
        new_fp = new_pages.get(rel)
        old_lines = _read_lines(old_fp) if old_fp else []
        new_lines = _read_lines(new_fp) if new_fp else []

        if old_fp is None:
            status = "added"
        elif new_fp is None:
            status = "removed"
        elif _normalize_for_diff(old_lines) == _normalize_for_diff(new_lines):
            status = "unchanged"
        else:
            status = "changed"

        diff_text = ""
        if status in ("added", "removed", "changed"):
            ud = difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
                n=context_lines,
                lineterm="",
            )
            diff_text = "\n".join(ud)

        diff.pages.append(
            WikiPageDiff(
                relpath=rel,
                status=status,
                old_lines=len(old_lines),
                new_lines=len(new_lines),
                diff_text=diff_text,
            )
        )
    return diff
