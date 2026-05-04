"""Diff engine: compare old vs. new emit + core-JSON dumps."""

from artificer.diff.wiki_diff import WikiDiff, WikiPageDiff, diff_emit_dirs
from artificer.diff.json_diff import (
    diff_core_dirs,
    JsonDiffEntry,
    render_unified_diff,
    split_lang_entries,
)
from artificer.diff.patch_article import render_patch_article, render_summary

__all__ = [
    "WikiDiff",
    "WikiPageDiff",
    "diff_emit_dirs",
    "diff_core_dirs",
    "JsonDiffEntry",
    "render_unified_diff",
    "split_lang_entries",
    "render_patch_article",
    "render_summary",
]
