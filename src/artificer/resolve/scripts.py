"""Parse ``.script`` files into Function/Statement records.

Format::

    <declared_type> <function_name>
    {
        Op1( arg1, arg2, ... )
        Op2( ... )
    }

Comments and whitespace are tolerated. Args can be quoted strings or
bareword identifiers (function refs, JSON paths, numeric literals, etc.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Statement:
    op: str
    args: tuple[str, ...]


@dataclass(frozen=True)
class Function:
    name: str
    declared_type: str
    body: tuple[Statement, ...]


_FUNC_RE = re.compile(
    r"(?ms)^\s*([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*\{([^}]*)\}"
)
_CALL_RE = re.compile(r"([A-Za-z_]\w*)\s*\((.*?)\)\s*", re.DOTALL)


def _split_args(inner: str) -> list[str]:
    """Top-level comma split, respecting quoted strings."""
    out: list[str] = []
    cur: list[str] = []
    in_str = False
    quote_ch = ""
    i = 0
    n = len(inner)
    while i < n:
        ch = inner[i]
        if in_str:
            if ch == "\\" and i + 1 < n:
                cur.append(ch)
                cur.append(inner[i + 1])
                i += 2
                continue
            if ch == quote_ch:
                in_str = False
                cur.append(ch)
                i += 1
                continue
            cur.append(ch)
            i += 1
            continue
        if ch in '"\'':
            in_str = True
            quote_ch = ch
            cur.append(ch)
            i += 1
            continue
        if ch == ",":
            out.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    tail = "".join(cur).strip()
    if tail:
        out.append(tail)
    # Strip surrounding quotes
    return [a.strip().strip('"').strip("'") if (a.startswith('"') or a.startswith("'")) else a.strip() for a in out]


class ScriptRegistry:
    """Function name → Function. Built once per pipeline run."""

    def __init__(self) -> None:
        self._funcs: dict[str, Function] = {}

    def parse_dir(self, root: Path) -> None:
        for fp in sorted(root.rglob("*.script")):
            try:
                text = fp.read_text(encoding="utf-8-sig", errors="replace")
            except Exception:
                continue
            self.parse_text(text)

    def parse_text(self, text: str) -> None:
        for fm in _FUNC_RE.finditer(text):
            decl, name, body = fm.group(1), fm.group(2), fm.group(3)
            statements: list[Statement] = []
            for cm in _CALL_RE.finditer(body):
                op = cm.group(1)
                args = _split_args(cm.group(2))
                statements.append(Statement(op=op, args=tuple(args)))
            self._funcs[name] = Function(
                name=name, declared_type=decl, body=tuple(statements)
            )

    def get(self, name: str) -> Function | None:
        return self._funcs.get(name)

    def __len__(self) -> int:
        return len(self._funcs)
