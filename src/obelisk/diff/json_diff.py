"""Structural diff between two core JSON dumps.

Walks both ``Core/`` trees, finds every ``*.json`` file present in either,
and produces a flat list of change entries:

* ``file_added`` / ``file_removed`` — file present only on one side
* ``value_added`` / ``value_removed`` / ``value_changed`` — leaf-level deltas
  inside a shared file

Entries can be rendered as either a one-line-per-change format
(``JsonDiffEntry.format``) or as a unified-diff-format string
(``render_unified_diff``). The CLI uses the unified format and splits the
output into ``complete.diff`` (non-localization) and ``localization.diff``
(``Lang/`` only) so reviewers can skim the meaty changes without wading
through translation churn.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


@dataclass(frozen=True)
class JsonDiffEntry:
    """One leaf-level change between two JSON dumps."""

    file: str
    kind: str  # file_added | file_removed | value_added | value_removed | value_changed
    path: str = ""
    old: Any = None
    new: Any = None

    def format(self) -> str:
        """Compact one-line rendering (legacy)."""
        if self.kind == "file_added":
            return f"+ {self.file}  (new file)"
        if self.kind == "file_removed":
            return f"- {self.file}  (removed)"
        head = f"{self.file}: {self.path}"
        if self.kind == "value_added":
            return f"+ {head} = {_fmt(self.new)}"
        if self.kind == "value_removed":
            return f"- {head} = {_fmt(self.old)}"
        if self.kind == "value_changed":
            return f"~ {head}: {_fmt(self.old)} -> {_fmt(self.new)}"
        return f"? {head}"


def _fmt(v: Any) -> str:
    """JSON-style rendering for diff line bodies.

    Strings come out quoted, numbers/bools/null bare, dicts and lists
    compact-encoded. Matches the source file conventions and lets
    syntax-highlighting editors color values correctly.
    """
    try:
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return repr(v)


def _list_json(root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    if not root.is_dir():
        return out
    for fp in root.rglob("*.json"):
        rel = fp.relative_to(root).as_posix()
        out[rel] = fp
    return out


def _load(fp: Path) -> Any:
    try:
        with fp.open(encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def _walk(
    a: Any,
    b: Any,
    path: str,
) -> Iterator[tuple[str, str, Any, Any]]:
    """Yield (kind, path, old, new) tuples for leaf-level differences."""
    if isinstance(a, dict) and isinstance(b, dict):
        keys = sorted(set(a) | set(b))
        for k in keys:
            sub_path = f"{path}.{k}" if path else k
            if k not in a:
                yield ("value_added", sub_path, None, b[k])
            elif k not in b:
                yield ("value_removed", sub_path, a[k], None)
            else:
                yield from _walk(a[k], b[k], sub_path)
        return
    if isinstance(a, list) and isinstance(b, list):
        # Try keyed alignment first. The game JSON uses ``id`` for entity
        # arrays (units, buffs, ...) and ``sid`` for localization arrays.
        # Aligning by the key field keeps a single insertion mid-array
        # from cascading into N positional "diffs."
        key_field = _common_key_field(a, b)
        if key_field is not None:
            a_by_key = {x[key_field]: x for x in a}
            b_by_key = {x[key_field]: x for x in b}
            for k in sorted(set(a_by_key) | set(b_by_key)):
                sub_path = f"{path}[{key_field}={k}]"
                if k not in a_by_key:
                    yield ("value_added", sub_path, None, b_by_key[k])
                elif k not in b_by_key:
                    yield ("value_removed", sub_path, a_by_key[k], None)
                else:
                    yield from _walk(a_by_key[k], b_by_key[k], sub_path)
            return
        # Positional alignment for primitive lists / mixed arrays.
        n = max(len(a), len(b))
        for i in range(n):
            sub_path = f"{path}[{i}]"
            if i >= len(a):
                yield ("value_added", sub_path, None, b[i])
            elif i >= len(b):
                yield ("value_removed", sub_path, a[i], None)
            else:
                yield from _walk(a[i], b[i], sub_path)
        return
    if a != b:
        yield ("value_changed", path, a, b)


_KEY_FIELDS: tuple[str, ...] = ("id", "sid", "key")


def _common_key_field(a: list, b: list) -> str | None:
    """First key field where every item in both lists has it as a string."""
    if not a or not b:
        return None
    for field in _KEY_FIELDS:
        a_ok = all(isinstance(x, dict) and isinstance(x.get(field), str) for x in a)
        b_ok = all(isinstance(x, dict) and isinstance(x.get(field), str) for x in b)
        if a_ok and b_ok:
            return field
    return None


def _all_have_id(items: list) -> bool:
    """Legacy: kept for callers that haven't switched to ``_common_key_field``."""
    return _common_key_field(items, items) == "id"


def split_lang_entries(
    entries: list[JsonDiffEntry],
) -> tuple[list[JsonDiffEntry], list[JsonDiffEntry]]:
    """Partition entries into (non-localization, localization)."""
    other: list[JsonDiffEntry] = []
    lang: list[JsonDiffEntry] = []
    for e in entries:
        if e.file.startswith("Lang/"):
            lang.append(e)
        else:
            other.append(e)
    return other, lang


def render_unified_diff(entries: list[JsonDiffEntry]) -> str:
    """Render entries as a unified-diff-format string.

    Layout per file::

        --- a/<file>
        +++ b/<file>
        @@ <json.path> @@
        -<old value>
        +<new value>

    For ``file_added`` / ``file_removed`` the headers point at
    ``/dev/null`` on the missing side and the body is empty.

    No surrounding context — there isn't any, since we're synthesizing
    the diff from a structural walk rather than from a textual diff. But
    the format still works in editors with diff syntax highlighting.
    """
    by_file: dict[str, list[JsonDiffEntry]] = {}
    for e in entries:
        by_file.setdefault(e.file, []).append(e)

    chunks: list[str] = []
    for file, file_entries in sorted(by_file.items()):
        first = file_entries[0]
        if first.kind == "file_added":
            chunks.append(f"--- /dev/null\n+++ b/{file}\n")
            continue
        if first.kind == "file_removed":
            chunks.append(f"--- a/{file}\n+++ /dev/null\n")
            continue

        lines: list[str] = [f"--- a/{file}", f"+++ b/{file}"]
        for e in file_entries:
            lines.append(f"@@ {e.path} @@")
            if e.kind == "value_changed":
                lines.append(f"-{_fmt(e.old)}")
                lines.append(f"+{_fmt(e.new)}")
            elif e.kind == "value_added":
                lines.append(f"+{_fmt(e.new)}")
            elif e.kind == "value_removed":
                lines.append(f"-{_fmt(e.old)}")
        chunks.append("\n".join(lines) + "\n")

    return "".join(chunks)


def diff_core_dirs(
    old_root: Path,
    new_root: Path,
) -> list[JsonDiffEntry]:
    """Diff every JSON file under ``Core/`` of two patch dumps."""
    a = old_root / "Core" if (old_root / "Core").is_dir() else old_root
    b = new_root / "Core" if (new_root / "Core").is_dir() else new_root

    a_files = _list_json(a)
    b_files = _list_json(b)
    all_rel = sorted(set(a_files) | set(b_files))

    entries: list[JsonDiffEntry] = []
    for rel in all_rel:
        if rel not in a_files:
            entries.append(JsonDiffEntry(file=rel, kind="file_added", new=None))
            continue
        if rel not in b_files:
            entries.append(JsonDiffEntry(file=rel, kind="file_removed", old=None))
            continue
        a_doc = _load(a_files[rel])
        b_doc = _load(b_files[rel])
        if a_doc is None or b_doc is None:
            continue
        for kind, path, old, new in _walk(a_doc, b_doc, ""):
            entries.append(JsonDiffEntry(file=rel, kind=kind, path=path, old=old, new=new))
    return entries
