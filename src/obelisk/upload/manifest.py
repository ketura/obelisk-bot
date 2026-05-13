"""Manifest builders for the uploader.

Two flavors share a wire format:

* Diff manifest — produced by ``obelisk diff`` for patch cycles.
  Pages list the changed pages between two extracts plus a patch
  article entry. Lives at ``out/<new>/diff_vs_<old>/manifest.json``.

* Full manifest — produced by ``obelisk generate`` for initial
  population or any "push everything" scenario. Pages list every wiki
  page in an extract dir, status ``added``. Lives at
  ``out/<label>/manifest.json``. No patch article.

Both flavors:

.. code-block:: json

    {
      "kind": "full" | "diff",
      "label": "<new label>",
      "old_label": "<old label or null>",
      "patch_article": {"title": "...", "path": "..."} | null,
      "pages": [
        {"title": "Data:Unit/angel", "relpath": "data/units/angel.wiki.txt",
         "status": "added"},
        ...
      ]
    }

The uploader treats both shapes uniformly. The ``kind`` field is
informational; everything else the uploader needs is in ``pages`` and
``patch_article``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from obelisk.diff import wiki_title_for_relpath


@dataclass(frozen=True)
class ManifestEntry:
    title: str
    relpath: str
    status: str  # added | changed | removed (full manifests use 'added')


@dataclass
class Manifest:
    kind: str  # "full" | "diff"
    label: str
    pages: list[ManifestEntry] = field(default_factory=list)
    old_label: str | None = None
    patch_article: dict | None = None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "label": self.label,
            "old_label": self.old_label,
            "patch_article": self.patch_article,
            "pages": [
                {"title": e.title, "relpath": e.relpath, "status": e.status}
                for e in self.pages
            ],
        }

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def build_full_manifest(
    extract_dir: Path,
    *,
    label: str | None = None,
    include_coverage: bool = True,
    include_cargo_templates: bool = True,
) -> Manifest:
    """Walk ``extract_dir`` and return a Manifest covering every wiki page.

    Includes every ``*.wiki.txt`` under ``data/`` (or ``Data/`` for
    legacy emit dirs). Optionally includes ``coverage.wiki.txt`` at the
    extract root (default on — its wiki home is ``Data:Coverage``) and
    every ``*.wiki.txt`` under ``cargo_templates/`` (default on — each
    wiki home is ``Template:<basename>``). The cargo templates are
    copied into the extract dir by ``obelisk generate`` from the
    project's ``docs/cargo/`` tree; this function only walks whatever
    happens to be there.

    Pages whose relpath can't be mapped to a wiki title are skipped with
    no warning; the upload layer can't push them anyway. (Currently
    this only catches ``audit.json`` and ``_meta.json`` style
    siblings — neither is a ``.wiki.txt`` so they're already
    out, but the guard is cheap.)

    Pages are sorted by title for stable, diff-friendly manifest
    output.
    """
    final_label = label or extract_dir.name
    # Dedupe by relpath. On case-insensitive filesystems (Windows,
    # default macOS) the legacy "Data" probe collides with the
    # canonical "data" dir and we'd walk every file twice. Keying by
    # the lowercased relpath also catches any other casing weirdness.
    seen: dict[str, ManifestEntry] = {}

    # Walk the data/ tree.
    for root_name in ("data", "Data"):
        data_dir = extract_dir / root_name
        if not data_dir.is_dir():
            continue
        for fp in data_dir.rglob("*.wiki.txt"):
            rel = fp.relative_to(extract_dir).as_posix()
            key = rel.lower()
            if key in seen:
                continue
            title = wiki_title_for_relpath(rel)
            if not title:
                continue
            seen[key] = ManifestEntry(title=title, relpath=rel, status="added")

    # Top-level extract pages (coverage today; extensible later).
    if include_coverage:
        cov = extract_dir / "coverage.wiki.txt"
        if cov.is_file():
            title = wiki_title_for_relpath("coverage.wiki.txt")
            if title and "coverage.wiki.txt" not in seen:
                seen["coverage.wiki.txt"] = ManifestEntry(
                    title=title, relpath="coverage.wiki.txt", status="added",
                )

    # Cargo template docs -> Template namespace.
    if include_cargo_templates:
        ct_dir = extract_dir / "cargo_templates"
        if ct_dir.is_dir():
            for fp in sorted(ct_dir.glob("*.wiki.txt")):
                rel = fp.relative_to(extract_dir).as_posix()
                key = rel.lower()
                if key in seen:
                    continue
                title = wiki_title_for_relpath(rel)
                if not title:
                    continue
                seen[key] = ManifestEntry(title=title, relpath=rel, status="added")

    entries = sorted(seen.values(), key=lambda e: e.title)
    return Manifest(kind="full", label=final_label, pages=entries)
