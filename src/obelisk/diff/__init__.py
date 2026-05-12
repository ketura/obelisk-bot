"""Diff engine: compare old vs. new emit + core-JSON dumps."""

from obelisk.diff.wiki_diff import (
    DIR_TO_WIKI_TABLE,
    WikiDiff,
    WikiPageDiff,
    diff_emit_dirs,
    wiki_title_for_relpath,
)
from obelisk.diff.json_diff import (
    diff_core_dirs,
    JsonDiffEntry,
    render_unified_diff,
    split_lang_entries,
)
from obelisk.diff.patch_article import render_patch_article, render_summary

__all__ = [
    "DIR_TO_WIKI_TABLE",
    "WikiDiff",
    "WikiPageDiff",
    "diff_emit_dirs",
    "wiki_title_for_relpath",
    "diff_core_dirs",
    "JsonDiffEntry",
    "render_unified_diff",
    "split_lang_entries",
    "render_patch_article",
    "render_summary",
]
