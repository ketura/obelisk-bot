"""HTML -> MediaWiki tag conversion plus light text normalization.

The L10n corpus uses HTML tags (``<b>``, ``<i>``) inline. The wiki uses
its own bold/italic syntax (``'''X'''`` and ``''X''``). Convert at resolve
time so wikitext output renders correctly.

We also flatten U+00A0 (non-breaking space) to a regular space. Unfrozen
uses NBSP for in-game typography (keeping ``[ 5 ]`` from line-wrapping at
the bracket); on the wiki the data renders in narrower contexts than the
game UI, and preserving NBSP causes layout snafus in our infoboxes. The
typographical intent isn't worth chasing.

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


def html_to_wiki(text: str) -> str:
    """Convert ``<b>``/``<i>`` to MediaWiki bold/italic, flatten NBSP,
    rewrite embedded newlines to ``<br/>``."""
    if not text:
        return text
    text = _BOLD_RE.sub(r"'''\1'''", text)
    text = _ITALIC_RE.sub(r"''\1''", text)
    text = text.replace("\xa0", " ")
    text = _NEWLINE_RE.sub("<br/>", text)
    return text
