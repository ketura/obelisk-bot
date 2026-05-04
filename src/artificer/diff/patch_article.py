"""Render the patch wiki article + operator summary."""

from __future__ import annotations

from artificer.diff.wiki_diff import WikiDiff, WikiPageDiff


# Display name for each entity type. Add as new emitters come online.
_ENTITY_HEADINGS: dict[str, str] = {
    "Unit": "Units",
    "Hero": "Heroes",
    "Spell": "Spells",
    "Item": "Items",
    "Building": "Buildings",
    "Faction": "Factions",
    "FactionLaw": "Faction Laws",
    "HeroSkill": "Hero Skills",
    "HeroSpecialization": "Hero Specializations",
    "Buff": "Buffs",
}


def _heading_for(entity_type: str) -> str:
    return _ENTITY_HEADINGS.get(entity_type, entity_type or "Misc")


def _wiki_link(page: WikiPageDiff) -> str:
    """Render a wiki link to the data page.

    The on-wiki page name strips the file extension and uses MediaWiki's
    title casing (the bot stores ``Data:Unit/<id>``).
    """
    et = page.entity_type or "Misc"
    return f"[[Data:{et}/{page.page_id}|{page.page_id}]]"


def render_patch_article(diff: WikiDiff, patch_label: str) -> str:
    """Build the wiki page body for ``Data:Patches/<patch_label>``.

    Layout: an intro line, then one section per entity type, each holding
    a bullet list of changed-page links plus an "Added" / "Removed"
    sub-section if those buckets are non-empty.
    """
    n_changed = len(diff.changed)
    n_added = len(diff.added)
    n_removed = len(diff.removed)

    lines: list[str] = []
    lines.append(f"<!-- Bot-managed page. Patch summary for {patch_label}. -->")
    lines.append("")
    lines.append(
        f"This page lists the data pages updated for patch '''{patch_label}'''. "
        f"{n_changed} changed, {n_added} added, {n_removed} removed."
    )
    lines.append("")

    grouped = diff.by_entity_type()
    # Stable heading order: known types in display order, then any unknown alphabetically.
    known_order = list(_ENTITY_HEADINGS.keys())
    type_order = [t for t in known_order if t in grouped]
    type_order += sorted(t for t in grouped if t not in known_order)

    for et in type_order:
        pages = grouped[et]
        if not pages:
            continue
        lines.append(f"== {_heading_for(et)} ==")
        added = [p for p in pages if p.status == "added"]
        removed = [p for p in pages if p.status == "removed"]
        changed = [p for p in pages if p.status == "changed"]

        if changed:
            for p in sorted(changed, key=lambda x: x.page_id):
                lines.append(f"* {_wiki_link(p)} ({p.hunk_summary})")
        if added:
            lines.append("")
            lines.append("'''Added:'''")
            for p in sorted(added, key=lambda x: x.page_id):
                lines.append(f"* {_wiki_link(p)}")
        if removed:
            lines.append("")
            lines.append("'''Removed:'''")
            for p in sorted(removed, key=lambda x: x.page_id):
                lines.append(f"* {p.page_id}")
        lines.append("")

    lines.append("[[Category:Patches]]")
    return "\n".join(lines) + "\n"


def render_summary(diff: WikiDiff, patch_label: str) -> str:
    """Operator-facing markdown summary."""
    lines: list[str] = []
    lines.append(f"# Patch cycle summary — {patch_label}")
    lines.append("")
    lines.append(f"- Changed: {len(diff.changed)}")
    lines.append(f"- Added: {len(diff.added)}")
    lines.append(f"- Removed: {len(diff.removed)}")
    lines.append(f"- Unchanged: {sum(1 for p in diff.pages if p.status == 'unchanged')}")
    lines.append("")
    grouped = diff.by_entity_type()
    if not grouped:
        lines.append("No changes detected.")
        return "\n".join(lines) + "\n"

    for et in sorted(grouped):
        pages = grouped[et]
        lines.append(f"## {_heading_for(et)} ({len(pages)})")
        lines.append("")
        lines.append("| page | status | +ins | -del | net |")
        lines.append("| --- | --- | ---: | ---: | ---: |")
        for p in sorted(pages, key=lambda x: x.page_id):
            lines.append(
                f"| {p.page_id} | {p.status} | {p.insertions} | {p.deletions} | {p.line_delta:+d} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"
