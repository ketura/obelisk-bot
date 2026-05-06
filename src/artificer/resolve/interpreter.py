"""Script function interpreter."""

from __future__ import annotations

import logging
import re
from typing import Any

from artificer.resolve.buffs import BuffIndex
from artificer.resolve.obstacles import ObstacleIndex
from artificer.resolve.scripts import Function, ScriptRegistry, Statement
from artificer.resolve.side_buffs import SideBuffIndex
from artificer.resolve.traps import TrapIndex

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
    if not path:
        return False
    if "bonuses[" in path and (".parameters[" in path or ".upgrade" in path):
        return True
    return any(hint in path for hint in _NUMERIC_PATH_HINTS)


def _numeric_default(path: str) -> float:
    return 1.0 if path.endswith(".statDmgMult") else 0.0


class Interpreter:
    def __init__(self, registry, buffs=None, obstacles=None, side_buffs=None, traps=None):
        self.registry = registry
        self.buffs = buffs
        self.obstacles = obstacles
        self.side_buffs = side_buffs
        self.traps = traps

    def evaluate(self, func_name, context):
        fn = self.registry.get(func_name)
        if fn is None:
            return None
        env = {}
        for stmt in fn.body:
            if not self._exec(stmt, context, env):
                return None
        if "return" not in env:
            return None
        return self._format(fn.declared_type, env["return"])

    def _exec(self, stmt, context, env):
        op = stmt.op
        args = stmt.args

        if op == "Text":
            if len(args) < 2: return False
            env[args[0]] = self._resolve_operand(args[1], env)
            return True

        if op in ("CurrentUnitConfig", "CurrentUnitData"):
            if len(args) < 2: return False
            target, path = args[0], args[1]
            v = self._read_path(context.get("unit_json"), path)
            if v is None and _looks_numeric_config(path): v = _numeric_default(path)
            env[target] = v
            return v is not None

        if op == "CurrentAbility":
            if len(args) < 2: return False
            target, path = args[0], args[1]
            v = self._read_path(context.get("ability_json"), path)
            if v is None and _looks_numeric_config(path): v = _numeric_default(path)
            env[target] = v
            return v is not None

        if op == "CurrentHeroSpecializationConfig":
            if len(args) < 2: return False
            target, path = args[0], args[1]
            v = self._read_path(context.get("spec_json"), path)
            if v is None and _looks_numeric_config(path): v = _numeric_default(path)
            env[target] = v
            return v is not None

        if op == "CurrentItem":
            if len(args) < 2: return False
            target, path = args[0], args[1]
            v = self._read_path(context.get("artifact_json"), path)
            if v is None and _looks_numeric_config(path): v = _numeric_default(path)
            env[target] = v
            return v is not None

        if op == "CurrentItemSet":
            if len(args) < 2: return False
            target, path = args[0], args[1]
            v = self._read_path(context.get("set_json"), path)
            if v is None and _looks_numeric_config(path): v = _numeric_default(path)
            env[target] = v
            return v is not None

        if op in ("CurrentMagicBattle", "CurrentMagicWorld"):
            if len(args) < 2: return False
            target, path = args[0], args[1]
            mj = context.get("magic_json") or {}
            raw = mj.get("raw") if isinstance(mj, dict) else None
            level = mj.get("level", 1) if isinstance(mj, dict) else 1
            try:
                level_idx = max(0, int(level) - 1)
            except (TypeError, ValueError):
                level_idx = 0
            sub = None
            if isinstance(raw, dict):
                if op == "CurrentMagicBattle":
                    bm = raw.get("battleMagic")
                    dealers = bm.get("magicDealers") if isinstance(bm, dict) else None
                    if isinstance(dealers, list) and dealers:
                        sub = dealers[min(level_idx, len(dealers) - 1)]
                else:
                    wm = raw.get("worldMagic")
                    if isinstance(wm, dict):
                        settings = wm.get("magicSettings")
                        per_levels = wm.get("settingPerLevels")
                        if isinstance(settings, list) and settings and isinstance(per_levels, list) and per_levels:
                            si = per_levels[min(level_idx, len(per_levels) - 1)]
                            if isinstance(si, int) and 0 <= si < len(settings):
                                sub = settings[si]
                        elif isinstance(settings, list) and settings:
                            sub = settings[min(level_idx, len(settings) - 1)]
            v = self._read_path(sub, path)
            if v is None and _looks_numeric_config(path): v = _numeric_default(path)
            env[target] = v
            return v is not None

        if op == "CurrentMagicBattleRoot":
            if len(args) < 2: return False
            target, path = args[0], args[1]
            mj = context.get("magic_json") or {}
            raw = mj.get("raw") if isinstance(mj, dict) else None
            v = self._read_path(raw, path)
            if v is None and _looks_numeric_config(path): v = _numeric_default(path)
            env[target] = v
            return v is not None

        if op == "CurrentMagicLevel":
            if len(args) < 1: return False
            target = args[0]
            mj = context.get("magic_json") or {}
            level = mj.get("level", 1) if isinstance(mj, dict) else 1
            try:
                env[target] = int(level)
            except (TypeError, ValueError):
                env[target] = 1
            return True

        if op == "CurrentBuff":
            if len(args) < 2 or self.buffs is None: return False
            target, path = args[0], args[1]
            mj = context.get("magic_json") or {}
            raw = mj.get("raw") if isinstance(mj, dict) else None
            level = mj.get("level", 1) if isinstance(mj, dict) else 1
            try:
                level_idx = max(0, int(level) - 1)
            except (TypeError, ValueError):
                level_idx = 0
            buff_sid = None
            if isinstance(raw, dict):
                bm = raw.get("battleMagic")
                dealers = bm.get("magicDealers") if isinstance(bm, dict) else None
                if isinstance(dealers, list) and dealers:
                    dealer = dealers[min(level_idx, len(dealers) - 1)]
                    if isinstance(dealer, dict):
                        b = dealer.get("buff")
                        if isinstance(b, dict):
                            buff_sid = b.get("sid")
            if not isinstance(buff_sid, str): return False
            be = self.buffs.get(buff_sid)
            if be is None: return False
            v = self._read_path(be, path)
            if v is None and _looks_numeric_config(path): v = _numeric_default(path)
            env[target] = v
            return v is not None

        if op == "CurrentBuffSP":
            return False

        if op == "CurrentHero":
            # Hero-stat defaults — viewRadius=3 (vanilla), all other
            # heroStat.* fields default to 0 (no bonus). Lets baseline
            # spell descriptions resolve cleanly even though the actual
            # in-game value scales with the casting hero.
            if len(args) < 2: return False
            target, path = args[0], args[1]
            if path == "heroStat.viewRadius":
                env[target] = 3
                return True
            if path.startswith("heroStat."):
                env[target] = 0
                return True
            return False

        if op == "DbBuff":
            if len(args) < 3 or self.buffs is None: return False
            target, sid_arg, path = args[0], args[1], args[2]
            buff_id = self._resolve_operand(sid_arg, env)
            if not isinstance(buff_id, str): return False
            buff = self.buffs.get(buff_id)
            if buff is None: return False
            v = self._read_path(buff, path)
            env[target] = v
            return v is not None

        if op == "DbTrap":
            if len(args) < 3 or self.traps is None: return False
            target, sid_arg, path = args[0], args[1], args[2]
            trap_id = self._resolve_operand(sid_arg, env)
            if not isinstance(trap_id, str): return False
            trap = self.traps.get(trap_id)
            if trap is None: return False
            v = self._read_path(trap, path)
            env[target] = v
            return v is not None

        if op == "DbSideBuff":
            if len(args) < 3 or self.side_buffs is None: return False
            target, info_arg, path = args[0], args[1], args[2]
            info_id = self._resolve_operand(info_arg, env)
            if not isinstance(info_id, str): return False
            base = self.side_buffs.get_effect(info_id)
            if base is None: return False
            v = self._read_path(base, path)
            env[target] = v
            return v is not None

        if op == "DbObstacle":
            if len(args) < 3 or self.obstacles is None: return False
            target, sid_arg, path = args[0], args[1], args[2]
            obs_id = self._resolve_operand(sid_arg, env)
            if not isinstance(obs_id, str): return False
            obstacle = self.obstacles.get(obs_id)
            if obstacle is None: return False
            v = self._read_path(obstacle, path)
            env[target] = v
            return v is not None

        if op == "CurrentUnitStats":
            if len(args) < 2: return False
            target, stat_name = args[0], args[1]
            stats = (context.get("unit_json") or {}).get("stats", {})
            v = stats.get(stat_name) if isinstance(stats, dict) else None
            env[target] = v
            return v is not None

        if op in ("Add", "Sub", "Mul", "Div", "Avg"):
            if len(args) < 3: return False
            target = args[0]
            ops = []
            for a in args[1:]:
                v = self._resolve_operand(a, env)
                try:
                    ops.append(float(v))
                except (ValueError, TypeError):
                    return False
            if not ops: return False
            if op == "Add": env[target] = sum(ops)
            elif op == "Sub": env[target] = ops[0] - sum(ops[1:])
            elif op == "Mul":
                v = 1.0
                for o in ops: v *= o
                env[target] = v
            elif op == "Div":
                if any(o == 0 for o in ops[1:]): return False
                v = ops[0]
                for o in ops[1:]: v /= o
                env[target] = v
            elif op == "Avg":
                env[target] = sum(ops) / len(ops)
            return True

        if op == "Floor":
            if len(args) < 2: return False
            target = args[0]
            v = self._resolve_operand(args[1], env)
            try:
                env[target] = int(float(v))
                return True
            except (ValueError, TypeError):
                return False

        if op == "Invoke":
            if len(args) < 2: return False
            target, name = args[0], args[1]
            result = self.evaluate(name, context)
            if result is None: return False
            env[target] = result
            return True

        logger.debug("unsupported script op: %s", op)
        return False

    def _resolve_operand(self, arg, env):
        if arg in env:
            return env[arg]
        try:
            f = float(arg)
            return int(f) if f.is_integer() else f
        except (ValueError, TypeError):
            return arg

    def _read_path(self, obj, path):
        if obj is None:
            return None
        tokens = re.findall(r"[A-Za-z_]\w*|\[\d+\]", path)
        cur = obj
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
        if isinstance(cur, dict) and set(cur.keys()) <= {"t", "v"} and "v" in cur:
            cur = cur["v"]
        return cur

    def _format(self, declared_type, raw):
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
