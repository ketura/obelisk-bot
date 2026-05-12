"""Tests for the per-namespace index page emitter."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from obelisk.diff import wiki_title_for_relpath
from obelisk.emit import DATA_IMPORT_CATEGORY, with_import_category
from obelisk.emit.index import (
    INDEX_FILENAME,
    load_index_blurbs,
    render_index_page,
    write_index_pages,
)
from obelisk.upload import build_full_manifest


# ---------------------------------------------------------------------------
# Wiki categories
# ---------------------------------------------------------------------------


def test_index_page_uses_indices_category() -> None:
    page = render_index_page("Unit", "Blurb.", ["angel"])
    assert "[[Category:Game Data Indices]]" in page
    # And NOT the import category (indexes get their own bucket).
    assert "[[Category:Game Data Import]]" not in page


def test_with_import_category_appends_tag() -> None:
    page = "{{Unit | id=angel}}\n"
    out = with_import_category(page)

    assert out.endswith("[[Category:Game Data Import]]\n")
    # Original content preserved.
    assert "{{Unit | id=angel}}" in out
    # Separated by a blank line.
    assert "}}\n\n[[Category:Game Data Import]]" in out


def test_with_import_category_is_idempotent() -> None:
    """A page that already has the tag isn't double-tagged."""
    page = "{{Unit | id=angel}}\n\n[[Category:Game Data Import]]\n"

    assert with_import_category(page) == page
    # Even after several applications.
    assert with_import_category(with_import_category(page)) == page


def test_with_import_category_constant_matches_tag() -> None:
    """The exported constant string is the literal category name used in pages."""
    assert DATA_IMPORT_CATEGORY == "Game Data Import"
    page = with_import_category("body")
    assert f"[[Category:{DATA_IMPORT_CATEGORY}]]" in page


# ---------------------------------------------------------------------------
# Title mapping
# ---------------------------------------------------------------------------


def test_wiki_title_for_index_page_is_bare_namespace() -> None:
    """The index landing page lives at Data:<Table>, not Data:<Table>/_index."""
    assert wiki_title_for_relpath("data/units/_index.wiki.txt") == "Data:Unit"
    assert wiki_title_for_relpath("data/factions/_index.wiki.txt") == "Data:Faction"
    assert wiki_title_for_relpath("data/movement/_index.wiki.txt") == "Data:Movement"


def test_wiki_title_for_entity_page_still_uses_subpage() -> None:
    """Regression: don't accidentally collapse normal entity titles."""
    assert wiki_title_for_relpath("data/units/angel.wiki.txt") == "Data:Unit/angel"


# ---------------------------------------------------------------------------
# Blurb file parsing
# ---------------------------------------------------------------------------


def test_load_index_blurbs_parses_section_per_header(tmp_path: Path) -> None:
    blurbs_file = tmp_path / "blurbs.md"
    blurbs_file.write_text(
        "# Top-level title\n\n"
        "Preamble that should be discarded.\n\n"
        "## Unit\n\n"
        "Units are the creatures heroes recruit.\n\n"
        "Each Data:Unit/<id> has stats.\n\n"
        "## Faction\n\n"
        "Single-line blurb.\n",
        encoding="utf-8",
    )

    blurbs = load_index_blurbs(blurbs_file)

    assert set(blurbs) == {"Unit", "Faction"}
    assert blurbs["Unit"].startswith("Units are the creatures")
    assert "Each Data:Unit/<id> has stats." in blurbs["Unit"]
    assert blurbs["Faction"] == "Single-line blurb."


def test_load_index_blurbs_missing_file_returns_empty_and_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)

    blurbs = load_index_blurbs(tmp_path / "nope.md")

    assert blurbs == {}
    assert any("index blurbs file not found" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Render output
# ---------------------------------------------------------------------------


def test_render_index_page_emits_blurb_and_sorted_bullets() -> None:
    page = render_index_page(
        "Unit",
        "Units are creatures.",
        ["imp", "angel", "angel_upg"],
    )

    assert page.startswith("<!-- Bot-managed page.")
    assert "Units are creatures." in page
    assert "== Pages (3) ==" in page
    # Sorted alphabetically.
    bullets_section = page.split("== Pages (3) ==")[1]
    angel_idx = bullets_section.index("Data:Unit/angel\n")  # plain angel, not _upg
    angel_upg_idx = bullets_section.index("Data:Unit/angel_upg")
    imp_idx = bullets_section.index("Data:Unit/imp")
    assert angel_idx < angel_upg_idx < imp_idx
    assert "[[Category:Data]]" in page


def test_render_index_page_converts_markdown_backticks_to_code_tags() -> None:
    """Blurbs are written as markdown; backticks must render as <code> in wiki."""
    page = render_index_page(
        "Unit",
        "Each `Data:Unit/<id>` page has `hp`, `damage`, etc.",
        ["angel"],
    )

    assert "<code>Data:Unit/&lt;id&gt;</code>" in page or "<code>Data:Unit/<id></code>" in page
    assert "<code>hp</code>" in page
    assert "<code>damage</code>" in page
    # And literal backticks are gone from the blurb area.
    blurb_section = page.split("== Pages")[0]
    assert "`" not in blurb_section


def test_render_index_page_falls_back_when_blurb_missing() -> None:
    page = render_index_page("Movement", None, ["fly", "walk"])

    assert "TODO" in page
    assert "Movement" in page
    # The list is still emitted normally.
    assert "[[Data:Movement/fly]]" in page
    assert "[[Data:Movement/walk]]" in page


def test_render_index_page_handles_empty_member_list() -> None:
    page = render_index_page("Difficulty", "The difficulties.", [])

    # No bullets, but still a sane page.
    assert "== Pages (0) ==" in page
    assert "(No pages in this namespace.)" in page


def test_render_index_page_dedupes_ids() -> None:
    page = render_index_page("Unit", "Blurb.", ["angel", "imp", "angel"])

    assert "== Pages (2) ==" in page
    # Each link appears exactly once.
    assert page.count("[[Data:Unit/angel]]") == 1


# ---------------------------------------------------------------------------
# write_index_pages: file output + dir walk
# ---------------------------------------------------------------------------


def _make_data_tree(root: Path) -> Path:
    """Synthesize the relevant subdirs of an extract."""
    data = root / "data"
    (data / "units").mkdir(parents=True)
    (data / "factions").mkdir(parents=True)
    (data / "units" / "angel.wiki.txt").write_text("x")
    (data / "units" / "imp.wiki.txt").write_text("y")
    (data / "factions" / "human.wiki.txt").write_text("z")
    return data


def test_write_index_pages_one_per_subdir(tmp_path: Path) -> None:
    data = _make_data_tree(tmp_path / "extract")

    counts = write_index_pages(
        data,
        dir_to_table={"units": "Unit", "factions": "Faction"},
        blurbs={"Unit": "Unit blurb.", "Faction": "Faction blurb."},
    )

    assert counts == {"Unit": 2, "Faction": 1}
    unit_idx = (data / "units" / INDEX_FILENAME).read_text(encoding="utf-8")
    assert "Unit blurb." in unit_idx
    assert "[[Data:Unit/angel]]" in unit_idx
    assert "[[Data:Unit/imp]]" in unit_idx
    faction_idx = (data / "factions" / INDEX_FILENAME).read_text(encoding="utf-8")
    assert "Faction blurb." in faction_idx
    assert "[[Data:Faction/human]]" in faction_idx


def test_write_index_pages_excludes_index_file_from_its_own_listing(
    tmp_path: Path,
) -> None:
    """Don't include _index.wiki.txt as a member of the namespace it lists."""
    data = _make_data_tree(tmp_path / "extract")
    # Simulate a stale _index file in the dir.
    (data / "units" / INDEX_FILENAME).write_text("stale")

    write_index_pages(
        data,
        dir_to_table={"units": "Unit", "factions": "Faction"},
        blurbs={"Unit": "x", "Faction": "y"},
    )

    unit_idx = (data / "units" / INDEX_FILENAME).read_text(encoding="utf-8")
    assert "Data:Unit/_index" not in unit_idx
    assert "Data:Unit/angel" in unit_idx


def test_write_index_pages_skips_unmapped_subdirs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    data = _make_data_tree(tmp_path / "extract")
    (data / "mystery").mkdir()
    (data / "mystery" / "thing.wiki.txt").write_text("?")
    caplog.set_level(logging.WARNING)

    counts = write_index_pages(
        data,
        dir_to_table={"units": "Unit", "factions": "Faction"},
        blurbs={"Unit": "x", "Faction": "y"},
    )

    assert "mystery" not in counts
    assert not (data / "mystery" / INDEX_FILENAME).is_file()
    assert any("no wiki-table mapping" in r.message for r in caplog.records)


def test_write_index_pages_logs_when_blurb_missing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    data = _make_data_tree(tmp_path / "extract")
    caplog.set_level(logging.WARNING)

    write_index_pages(
        data,
        dir_to_table={"units": "Unit", "factions": "Faction"},
        blurbs={"Unit": "x"},  # Faction blurb missing
    )

    # Placeholder body still rendered, but a warning fires.
    assert any(
        "blurb missing for table 'Faction'" in r.message for r in caplog.records
    )
    faction_idx = (data / "factions" / INDEX_FILENAME).read_text(encoding="utf-8")
    assert "TODO" in faction_idx


# ---------------------------------------------------------------------------
# Manifest pickup: end-to-end shape check
# ---------------------------------------------------------------------------


def test_full_manifest_picks_up_index_pages(tmp_path: Path) -> None:
    """An index file written to data/<x>/_index.wiki.txt should appear in
    the full manifest with the bare Data:<Table> title."""
    extract = tmp_path / "extract"
    data = _make_data_tree(extract)
    write_index_pages(
        data,
        dir_to_table={"units": "Unit", "factions": "Faction"},
        blurbs={"Unit": "x", "Faction": "y"},
    )

    manifest = build_full_manifest(extract, include_coverage=False)

    titles = {e.title for e in manifest.pages}
    assert "Data:Unit" in titles
    assert "Data:Faction" in titles
    # And the entity pages are still there alongside the indexes.
    assert "Data:Unit/angel" in titles
    assert "Data:Faction/human" in titles
    # Index entry's relpath points to the actual file on disk.
    unit_idx_entry = next(e for e in manifest.pages if e.title == "Data:Unit")
    assert unit_idx_entry.relpath == "data/units/_index.wiki.txt"
