"""Generic helpers for rendering Cargo-template invocations as wikitext.

Per D-013:
* Named parameters only: ``{{Unit | id=angel | hp=225}}``.
* Sparse output: parameters with empty/None values are omitted.
* Bot owns parameter order: rendering is deterministic given input + the
  caller's specified key order.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

from obelisk.resolve.wikitext import normalize_name


# Wikitext characters that break template syntax inside parameter values.
# We replace with HTML entities so the value renders literally on the page
# without breaking template parsing.
_WIKITEXT_ESCAPES = {
    "|": "&#124;",
    "=": "&#61;",
    "{{": "&#123;&#123;",
    "}}": "&#125;&#125;",
}

# Field keys whose value is the canonical English name and gets reused as
# a filename for icons/images on the wiki side. Smart apostrophes get
# flattened to ASCII for those keys only — per-language siblings
# (pt_br_name, cs_name, ...) keep their typography because they're pure
# display, never filename-fodder.
_NAME_FIELDS: frozenset[str] = frozenset({"name", "display_name"})


def render_value(value: Any) -> str:
    """Convert one parameter value to a wikitext-safe string.

    Lists become comma-separated (Cargo's native list-of-string format).
    Booleans become 'yes'/'no' (Cargo's Boolean convention).
    None becomes '' (caller decides whether to skip via sparse mode).
    Dicts are JSON-encoded — though dicts shouldn't reach here in normal
    use; the emitter is supposed to flatten them before calling.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _escape(value)
    if isinstance(value, (list, tuple)):
        return ",".join(_escape(str(v)) for v in value if v is not None and v != "")
    if isinstance(value, dict):
        # Should be rare — caller likely wants flattening, not JSON.
        return _escape(json.dumps(value, sort_keys=True, separators=(",", ":")))
    return _escape(str(value))


def _escape(s: str) -> str:
    """Replace wikitext-syntactic characters with HTML entities."""
    for needle, repl in _WIKITEXT_ESCAPES.items():
        s = s.replace(needle, repl)
    return s


def render_call(
    template: str,
    params: Mapping[str, Any],
    *,
    sparse: bool = True,
    key_order: Iterable[str] | None = None,
) -> str:
    """Render one template invocation as a multi-line wikitext call.

    Format::

        {{Template
        | key1 = value1
        | key2 = value2
        }}

    Multi-line form is used unconditionally for readability and so that
    ``git diff`` and the bot's own diff engine show one parameter per line.

    Args:
        template: Template name without leading ``Template:`` and without
            the surrounding ``{{ }}``.
        params: Mapping of param-name → raw value. Values are passed through
            :func:`render_value`.
        sparse: When True (default), parameters whose rendered value is
            an empty string are omitted entirely. When False, every
            parameter is emitted with its (possibly empty) value.
        key_order: Optional explicit ordering of keys. Keys not in this list
            are appended in insertion order (i.e. dict iteration order)
            after the explicitly ordered ones. When ``None``, keys are
            emitted in dict iteration order.
    """
    if key_order is not None:
        ordered_keys: list[str] = []
        seen: set[str] = set()
        for k in key_order:
            if k in params and k not in seen:
                ordered_keys.append(k)
                seen.add(k)
        for k in params:
            if k not in seen:
                ordered_keys.append(k)
    else:
        ordered_keys = list(params.keys())

    lines: list[str] = [f"{{{{{template}"]
    for k in ordered_keys:
        value = params[k]
        if k in _NAME_FIELDS and isinstance(value, str):
            value = normalize_name(value)
        rendered = render_value(value)
        if sparse and rendered == "":
            continue
        lines.append(f"| {k} = {rendered}")
    lines.append("}}")
    return "\n".join(lines)


def block_hash(block: Any) -> str:
    """Stable short hash of any JSON-serializable structure.

    Used as a change-detection signal on Cargo rows that flatten complex
    blocks (passives, abilities, attacks). When the underlying JSON shape
    changes — even in a way our flattened columns don't capture — the hash
    differs and the diff engine surfaces it for review.

    Returns the first 8 hex characters of sha-256 over the canonicalized
    JSON form (sorted keys, no whitespace). 32 bits is plenty for our
    scale (~hundreds of blocks per release).
    """
    canonical = json.dumps(block, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest[:8]
