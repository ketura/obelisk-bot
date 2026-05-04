"""Script function interpreter.

Implements the operations used by the ``Lang/args/*.json`` mapped script
functions: literal text, JSON path reads, arithmetic, etc.

Operation coverage:

* ``Text(target, value-or-var)``                 - assign env var or literal
* ``CurrentUnitConfig(target, "json.path")``     - read from unit JSON
* ``CurrentUnitStats(target, "stat_name")``      - read from unit stats
* ``CurrentUnitData(target, "json.path")``       - alias of CurrentUnitConfig
* ``CurrentAbility(target, "json.path")``        - read from active ability JSON
* ``DbBuff(target, sid_var, "json.path")``       - look up a buff by id, then read path
* ``Add``/``Sub``/``Mul``/``Div``/``Avg``        - arithmetic
* ``Floor(target, value)``                       - integer floor
* ``Invoke(target, "funcname")``                 - call another function
"""

from __future__ import annotations

import logging
import re
from typing import Any

from artificer.resolve.buffs import BuffIndex
from artificer.resolve.obstacles import ObstacleIndex
from artificer.resolve.scripts import Function, ScriptRegistry, Statement
from artificer.resolve.side_buffs import SideBuffIndex

logger = logging.getLogger(__name__)


_NUMERIC_PATH_HINTS: tuple[str, ...] = (
    ".upgrade.",
    "upgrade.increment",
    ".increment",
    "durationPerStack",
    ".duration",
    ".values[",
    ".minBaseDmg",
    ".maxBaseDmg",
    ".minStackDmg",
    ".maxStackDmg",
    ".statDmgMult",
    ".damageMultiplerPerHeroLevel",
)


def _looks_numeric_config(path: str) -> bool:
    """Return True if this looks like a numeric-config JSON path.

    The game engine's behavior (per OldenEraExplorer's reference impl) is to
    silently substitute 0 for missing numeric config values, rather than
    fail the whole script. Our resolver mirrors this for paths that look
    plausibly numeric, leaving opaque-string paths to fail loudly.
    """
    if not path:
        return False
    if "bonuses[" in path and (".parameters[" in path or ".upgrade" in path):
        return True
    return any(hint in path for hint in _NUMERIC_PATH_HINTS)


def _numeric_default(path: str) -> float:
    """Default value for a missing numeric config path.

    Most paths default to 0; ``statDmgMult`` defaults to 1.0 (= 100% basic
    attack damage), matching the engine's "no override" semantics.
    """
    return 1.0 if path.endswith(".statDmgMult") else 0.0


class Interpreter:
    """Evaluates script functions against a unit-context dict.

    Context dict keys consumed by the operations:

    * ``unit_json``    - the full unit JSON (CurrentUnitConfig/Data/Stats).
    * ``ability_json`` - the active ability/passive JSON sub-tree (CurrentAbility).
    """

    def __init__(
        self,
        registry: ScriptRegistry,
        buffs: BuffIndex | None = None,
        obstacles: ObstacleIndex | None = None,
        side_buffs: SideBuffIndex | None = None,
    ) -> None:
        self.registry = registry
        self.buffs = buffs
        self.obstacles = obstacles
        self.side_buffs = side_buffs

    def evaluate(self, func_name: str, context: dict[str, Any]) -> str | None:
        fn = self.registry.get(func_name)
        if fn is None:
            return None
        env: dict[str, Any] = {}
        for stmt in fn.body:
            if not self._exec(stmt, context, env):
                return None
        if "return" not in env:
            return None
        return self._format(fn.declared_type, env["return"])

    def _exec(
        self,
        stmt: Statement,
        context: dict[str, Any],
        env: dict[str, Any],
    ) -> bool:
        op = stmt.op
        args = stmt.args

        if op == "Text":
            # Text(target, value-or-var) - resolve env var first, else literal.
            # The script tokenizer strips quotes, so we can't distinguish a
            # quoted literal from a bareword reference at this point.
            if len(args) < 2:
                return False
            env[args[0]] = self._resolve_operand(args[1], env)
            return True

        if op in ("CurrentUnitConfig", "CurrentUnitData"):
            if len(args) < 2:
                return False
            target, path = args[0], args[1]
            value = self._read_path(context.get("unit_json"), path)
            if value is None and _looks_numeric_config(path):
                value = _numeric_default(path)
            env[target] = value
            return value is not None

        if op == "CurrentAbility":
            if len(args) < 2:
                return False
            target, path = args[0], args[1]
            value = self._read_path(context.get("ability_json"), path)
            if value is None and _looks_numeric_config(path):
                value = _numeric_default(path)
            env[target] = value
            return value is not None

        if op == "DbBuff":
            if len(args) < 3 or self.buffs is None:
                return False
            target, sid_arg, path = args[0], args[1], args[2]
            buff_id = self._resolve_operand(sid_arg, env)
            if not isinstance(buff_id, str):
                return False
            buff = self.buffs.get(buff_id)
            if buff is None:
                return False
            value = self._read_path(buff, path)
            env[target] = value
            return value is not None

        if op == "DbSideBuff":
            # DbSideBuff(target, info_id, "json.path") — looks info_id up in
            # side_buff_infos, follows its sid to the matching side_buff_base,
            # and reads json.path from the base.
            if len(args) < 3 or self.side_buffs is None:
                return False
            target, info_arg, path = args[0], args[1], args[2]
            info_id = self._resolve_operand(info_arg, env)
            if not isinstance(info_id, str):
                return False
            base = self.side_buffs.get_effect(info_id)
            if base is None:
                return False
            value = self._read_path(base, path)
            env[target] = value
            return value is not None

        if op == "DbObstacle":
            if len(args) < 3 or self.obstacles is None:
                return False
            target, sid_arg, path = args[0], args[1], args[2]
            obs_id = self._resolve_operand(sid_arg, env)
            if not isinstance(obs_id, str):
                return False
            obstacle = self.obstacles.get(obs_id)
            if obstacle is None:
                return False
            value = self._read_path(obstacle, path)
            env[target] = value
            return value is not None

        if op == "CurrentUnitStats":
            if len(args) < 2:
                return False
            target, stat_name = args[0], args[1]
            stats = (context.get("unit_json") or {}).get("stats", {})
            value = stats.get(stat_name) if isinstance(stats, dict) else None
            env[target] = value
            return value is not None

        if op in ("Add", "Sub", "Mul", "Div", "Avg"):
            if len(args) < 3:
                return False
            target = args[0]
            operands: list[float] = []
            for a in args[1:]:
                v = self._resolve_operand(a, env)
                try:
                    operands.append(float(v))
                except (ValueError, TypeError):
                    return False
            if not operands:
                return False
            if op == "Add":
                env[target] = sum(operands)
            elif op == "Sub":
                env[target] = operands[0] - sum(operands[1:])
            elif op == "Mul":
                v = 1.0
                for o in operands:
                    v *= o
                env[target] = v
            elif op == "Div":
                if any(o == 0 for o in operands[1:]):
                    return False
                v = operands[0]
                for o in operands[1:]:
                    v /= o
                env[target] = v
            elif op == "Avg":
                env[target] = sum(operands) / len(operands)
            return True

        if op == "Floor":
            if len(args) < 2:
                return False
            target = args[0]
            v = self._resolve_operand(args[1], env)
            try:
                env[target] = int(float(v))
                return True
            except (ValueError, TypeError):
                return False

        if op == "Invoke":
            if len(args) < 2:
                return False
            target, name = args[0], args[1]
            result = self.evaluate(name, context)
            if result is None:
                return False
            env[target] = result
            return True

        logger.debug("unsupported script op: %s", op)
        return False

    def _resolve_operand(self, arg: str, env: dict[str, Any]) -> Any:
        if arg in env:
            return env[arg]
        try:
            f = float(arg)
            return int(f) if f.is_integer() else f
        except (ValueError, TypeError):
            return arg

    def _read_path(self, obj: Any, path: str) -> Any:
        if obj is None:
            return None
        tokens = re.findall(r"[A-Za-z_]\w*|\[\d+\]", path)
        cur: Any = obj
        for tok in tokens:
            if cur is None:
                return None
            if tok.startswith("["):
                idx = int(tok[1:-1])
                if isinstance(cur, list) and 0 <= idx < len(cur):
                    cur = cur[idx]
                else:
                    return None
            else:
                if isinstance(cur, dict):
                    cur = cur.get(tok)
                else:
                    return None
        # Auto-unwrap {"v": x} wrappers (game JSON uses this for typed list items)
        if isinstance(cur, dict) and set(cur.keys()) <= {"t", "v"} and "v" in cur:
            cur = cur["v"]
        return cur

    def _format(self, declared_type: str, raw: Any) -> str:
        if isinstance(raw, str) and declared_type == "string":
            return raw
        try:
            num = float(raw)
        except (ValueError, TypeError):
            return str(raw) if raw is not None else ""
        if declared_type == "modPercentNumeric":
            return str(round(abs(num) * 100))
        if declared_type == "modFloatPercentF1Numeric":
            v = abs(num) * 100
            text = f"{v:.1f}"
            return text.rstrip("0").rstrip(".") if "." in text else text
        if declared_type == "modInt":
            return str(round(abs(num)))
        if declared_type == "int":
            return str(round(num))
        if declared_type == "float":
            return f"{num:g}"
        return str(raw)
