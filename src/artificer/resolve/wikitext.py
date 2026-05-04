"""HTML -> MediaWiki tag conversion plus light text normalization.

The L10n corpus uses HTML tags (``<b>``, ``<i>``) inline. The wiki uses
its own bold/italic syntax (``'''X'''`` and ``''X''``). Convert at resolve
time so wikitext output renders correctly.

We also flatten U+00A0 (non-breaking space) to a regular space. Unfrozen
uses NBSP for in-game typography (keeping ``[ 5 ]`` from line-wrapping at
the bracket); on the wiki the data renders in narrower contexts than the
game UI, and preserving NBSP causes layout snafus in our infoboxes. The
typographical intent isn't worth chasing.
"""

from __future__ import annotations

import re

_BOLD_RE = re.compile(r"<b>(.*?)</b>", re.DOTALL | re.IGNORECASE)
_ITALIC_RE = re.compile(r"<i>(.*?)</i>", re.DOTALL | re.IGNORECASE)


def html_to_wiki(text: str) -> str:
    """Convert ``<b>``/``<i>`` to MediaWiki bold/italic; flatten NBSP."""
    if not text:
        return text
    text = _BOLD_RE.sub(r"'''\1'''", text)
    text = _ITALIC_RE.sub(r"''\1''", text)
    text = text.replace(" ", " ")
    return text
