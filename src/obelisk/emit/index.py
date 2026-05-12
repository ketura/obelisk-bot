"""Per-namespace index pages.

For every `Data:<Table>/<id>` namespace the bot emits, there's a
parallel `Data:<Table>` index page listing every member. The index
page carries a hand-authored blurb (from ``docs/index_blurbs.md``)
above the auto-generated link list.

On-disk layout::

    out/<label>/data/<type>/_index.wiki.txt

The ``_`` prefix matches the existing ``_orphan_sub_skills`` convention
and keeps the index out of any future collision with an entity named
"index". The mapping ``data/<type>/_index.wiki.txt`` -> ``Data:<Table>``
(bare, no subpage) lives in :mod:`obelisk.diff.wiki_diff`.

Blurb file format: markdown with ``## <Table>`` section headers,
prose body. Section headers must match the wiki table name exactly
(e.g. ``## HeroSpecialization``). Unmatched sections are ignored;
unmatched namespaces fall back to a one-line placeholder and log a
warning.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from pathlib import Path

logger = logging.getLogger(__name__)


INDEX_FILENAME = "_index.wiki.txt"

# Convert markdown backtick spans (`foo`) to MediaWiki <code> tags.
# Keeps the blurbs file editable as regular markdown while rendering
# correctly on the wiki side. Non-greedy match within a single line —
# we don't span code across newlines.
_BACKTICK_RE = re.compile(r"`([^`\n]+?)`")


def _markdown_to_wikitext(text: str) -> str:
    """Light markdown -> wikitext conversion for the blurb body.

    Currently only handles inline code spans. Headers, lists, etc. are
    not used in the blurbs (each blurb is plain prose under a section
    header that we already strip during parsing), so the conversion is
    deliberately minimal.
    """
    return _BACKTICK_RE.sub(r"<code>\1</code>", text)


def load_index_blurbs(blurbs_path: Path) -> dict[str, str]:
    """Parse ``docs/index_blurbs.md`` into a ``{table_name: body}`` map.

    Sections start with ``## `` and run until the next ``## `` (or
    end-of-file). Any preamble before the first ``## `` is treated as
    file-level commentary and discarded. Body text is stripped of
    leading/trailing whitespace but preserves internal blank lines
    (paragraph breaks).

    Missing file: returns an empty map and logs a warning. The
    emitter then falls back to placeholder blurbs.
    """
    if not blurbs_path.is_file():
        logger.warning("index blurbs file not found: %s", blurbs_path)
        return {}

    text = blurbs_path.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    current_header: str | None = None
    current_body: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_header is not None:
                sections[current_header] = "\n".join(current_body).strip()
            current_header = line[3:].strip()
            current_body = []
        elif current_header is not None:
            current_body.append(line)
        # else: pre-first-header preamble, ignored

    if current_header is not None:
        sections[current_header] = "\n".join(current_body).strip()

    return sections


_BOT_BANNER = "<!-- Bot-managed page. Edit the source in obelisk-bot, not here. -->"


def render_index_page(
    table_name: str,
    blurb: str | None,
    page_ids: Iterable[str],
) -> str:
    """Render one Data:<Table> index page.

    ``table_name`` is the wiki-side namespace (e.g. ``Unit``).
    ``page_ids`` are the ids of every member page (e.g. ``angel``,
    ``angel_upg``); the renderer sorts them and emits one
    ``[[Data:<Table>/<id>]]`` bullet per id.

    Missing blurb falls back to a placeholder noting the blurb is
    pending so it's visible on the wiki.
    """
    ids = sorted(set(page_ids))

    if blurb:
        body_blurb = _markdown_to_wikitext(blurb)
    else:
        body_blurb = (
            f"<!-- TODO: blurb for {table_name} pending in docs/index_blurbs.md -->\n"
            f"''(Index for the [[:Category:Data|Data]]:{table_name} namespace. "
            f"Per-page blurb pending.)''"
        )

    bullets = "\n".join(f"* [[Data:{table_name}/{pid}]]" for pid in ids)
    if not bullets:
        bullets = "''(No pages in this namespace.)''"

    lines = [
        _BOT_BANNER,
        "",
        body_blurb,
        "",
        f"== Pages ({len(ids)}) ==",
        "",
        bullets,
        "",
        "[[Category:Game Data Indices]]",
        "",
    ]
    return "\n".join(lines)


def write_index_pages(
    data_dir: Path,
    *,
    dir_to_table: dict[str, str],
    blurbs: dict[str, str],
) -> dict[str, int]:
    """Walk ``data_dir`` and write one ``_index.wiki.txt`` per subdir.

    Page ids for each subdir are the basenames of its ``.wiki.txt``
    files, minus the ``.wiki.txt`` suffix and minus any ``_index`` /
    ``_orphan_*`` files (those are meta pages, not entities).

    ``dir_to_table`` maps the on-disk dir name to the wiki table name
    (the same map used by the diff engine). Subdirs not in the map
    are skipped with a warning — they wouldn't get a meaningful index
    title anyway.

    Returns ``{table_name: n_pages_listed}`` for the run-time
    summary.
    """
    counts: dict[str, int] = {}
    if not data_dir.is_dir():
        return counts

    for subdir in sorted(data_dir.iterdir()):
        if not subdir.is_dir():
            continue
        dir_name = subdir.name
        table = dir_to_table.get(dir_name)
        if table is None:
            logger.warning(
                "index skipped: %s has no wiki-table mapping", subdir
            )
            continue

        ids: list[str] = []
        for fp in subdir.iterdir():
            if not fp.is_file():
                continue
            name = fp.name
            if not name.endswith(".wiki.txt"):
                continue
            stem = name[: -len(".wiki.txt")]
            # Skip meta pages — _index is what we're writing now,
            # _orphan_* (e.g. skills/_orphan_sub_skills) are listed
            # by the index but as a distinct sub-bullet rather than
            # a regular entity (kept simple for v1; just include it
            # like any other entry).
            if stem == "_index":
                continue
            ids.append(stem)

        blurb = blurbs.get(table)
        if blurb is None:
            logger.warning(
                "index blurb missing for table %r — emitting placeholder",
                table,
            )

        page = render_index_page(table, blurb, ids)
        (subdir / INDEX_FILENAME).write_text(page, encoding="utf-8")
        counts[table] = len(ids)

    return counts
