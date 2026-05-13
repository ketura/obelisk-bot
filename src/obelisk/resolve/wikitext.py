"""HTML -> MediaWiki tag conversion plus light text normalization.

The L10n corpus uses HTML tags (``<b>``, ``<i>``) inline. The wiki uses
its own bold/italic syntax (``'''X'''`` and ``''X''``). Convert at resolve
time so wikitext output renders correctly.

We also normalize a handful of typographic Unicode characters Unfrozen
ships that look like ASCII but compare unequal. Wiki authors typing the
same name on a keyboard produce the ASCII version; the source data
produces the typographic version; flattening here keeps the two in
sync so cargo joins, page-name lookups, and file-name references all
match regardless of who authored the row.

Embedded newlines in leaf strings get rewritten to ``<br/>``. MediaWiki
collapses a lone newline to a space inside template parameters and
turns a blank line into a paragraph break — neither matches what the
source data means by a line break in a description. The explicit tag
renders consistently regardless of parameter context. ``\\r\\n`` /
``\\r`` are normalized too so a Windows-side L10n file doesn't surprise
us.
"""

from __future__ import annotations

import re

_BOLD_RE = re.compile(r"<b>(.*?)</b>", re.DOTALL | re.IGNORECASE)
_ITALIC_RE = re.compile(r"<i>(.*?)</i>", re.DOTALL | re.IGNORECASE)
# Match any newline shape — CRLF/CR/LF — in one pass.
_NEWLINE_RE = re.compile(r"\r\n|\r|\n")

# Typographic-Unicode normalizations. Each entry is (codepoint, replacement).
# Order doesn't matter (no entry produces another entry's source char).
# Add new cases when an "invisible difference" bug surfaces.
_TYPOGRAPHIC_NORMALIZE: tuple[tuple[str, str], ...] = (
    (" ", " "),    # NO-BREAK SPACE
    ("­", ""),     # SOFT HYPHEN (invisible, breaks string matching)
    ("‑", "-"),    # NON-BREAKING HYPHEN (caused the Zoran "Self‑Founded" bug)
    (" ", " "),    # NARROW NO-BREAK SPACE
    ("​", ""),     # ZERO WIDTH SPACE
    ("‌", ""),     # ZERO WIDTH NON-JOINER
    ("‍", ""),     # ZERO WIDTH JOINER
    ("⁠", ""),     # WORD JOINER (invisible)
    ("﻿", ""),     # ZERO WIDTH NO-BREAK SPACE / BOM
)


def html_to_wiki(text: str) -> str:
    """Convert ``<b>``/``<i>`` to MediaWiki bold/italic, normalize a
    set of typographic Unicode characters to their ASCII equivalents,
    rewrite embedded newlines to ``<br/>``."""
    if not text:
        return text
    text = _BOLD_RE.sub(r"'''\1'''", text)
    text = _ITALIC_RE.sub(r"''\1''", text)
    for src, dst in _TYPOGRAPHIC_NORMALIZE:
        if src in text:
            text = text.replace(src, dst)
    text = _NEWLINE_RE.sub("<br/>", text)
    return text


# Additional name-field-only normalization. Smart apostrophes (U+2018,
# U+2019) become ASCII U+0027 in name fields because names get used as
# filenames for icons/images on the wiki side, and a human typing on a
# keyboard can't easily produce the typographic apostrophe. The same
# rationale doesn't apply to descriptions/narrative text — those are
# pure display and the typography reads better preserved. Per-language
# name siblings (pt_br_name, cs_name, ...) are also left alone; only
# the English ``name`` and ``display_name`` columns get this treatment.
_NAME_NORMALIZE: tuple[tuple[str, str], ...] = (
    ("’", "'"),   # RIGHT SINGLE QUOTATION MARK
    ("‘", "'"),   # LEFT SINGLE QUOTATION MARK
)


def normalize_name(text):
    """Additional normalization layered on top of ``html_to_wiki`` for
    canonical English name fields. Flatten smart apostrophes to ASCII
    so the value is filename-safe and matches what a wiki author types.

    Pass-through on ``None`` / empty so callers can chain it onto an
    optional lookup result unconditionally.
    """
    if not text or not isinstance(text, str):
        return text
    for src, dst in _NAME_NORMALIZE:
        if src in text:
            text = text.replace(src, dst)
    return text
