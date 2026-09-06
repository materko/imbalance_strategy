"""Metadáta parametrov pre formulár — z Pine skriptu stratégie, nie ručne.

Formulár má ukazovať to isté, čo panel nastavení v TradingView: rovnaké skupiny,
rovnaké titulky, rovnaké tooltipy. Všetko to v Pine skripte už je, takže sa parsuje
odtiaľ (`StrategySpec.pine_path`) a k tomu sa pridajú polia, ktoré Pine nemá
(`config_cls.PORT_ONLY_FIELDS`, titulky v `spec.port_only_meta`). Keď niekto v Pine
zmení tooltip, formulár ho zmení tiež. Parser je spoločný pre všetky stratégie.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from ..core.types import SizeSpec
from ..strategies import STRATEGIES, StrategySpec, get_spec
from ..strategies.ibs import SPEC as IBS_SPEC

REPO = Path(__file__).resolve().parents[2]
#: Spätná kompatibilita — metadáta IBS bez argumentu.
PINE_FILE = IBS_SPEC.pine_path
REMOVED_INPUTS = IBS_SPEC.removed_inputs
FEATURES = IBS_SPEC.features

PORT_GROUP = "🧩 Rozšírenia portu (nie sú v Pine)"

_INPUT_RE = re.compile(r"^\s*(\w+)\s*=\s*input\.(\w+)\((.*)$")
_GROUP_ORDER_RE = re.compile(r'group\s*=\s*"([^"]*)"')


@dataclass
class ParamMeta:
    name: str
    type: str  # bool | int | float | string | color | size
    title: str
    group: str
    tooltip: str = ""
    default: Any = None
    options: list[str] | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    #: pre `size` polia: jednotka, v ktorej je hodnota v Pine (abs/ticks)
    pine_unit: str | None = None
    inline: str | None = None
    #: pole, ktoré Pine skript sám nepoužíva (napr. state4MaxBars) alebo je len vizuálne
    note: str = ""
    #: prepínače, z ktorých aspoň jeden musí byť zapnutý, aby malo pole zmysel (viď FEATURES)
    depends_on: list[str] | None = None
    #: kresliaci prepínač feature, ktorú toto pole zapína (zrkadlí sa vedľa neho)
    show_param: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _split_args(rest: str) -> list[str]:
    args: list[str] = []
    depth = 0
    cur = ""
    in_str = False
    for ch in rest:
        if in_str:
            cur += ch
            if ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            cur += ch
            continue
        if ch in "([":
            depth += 1
        elif ch in ")]":
            if depth == 0:
                break
            depth -= 1
        elif ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
            continue
        cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


def _kwargs(args: list[str]) -> tuple[list[str], dict[str, str]]:
    pos: list[str] = []
    kw: dict[str, str] = {}
    for a in args:
        m = re.match(r"^(\w+)\s*=\s*(.*)$", a, re.S)
        if m and m.group(1) not in ("true", "false"):
            kw[m.group(1)] = m.group(2).strip()
        else:
            pos.append(a)
    return pos, kw


def _unquote(s: str | None) -> str:
    if s is None:
        return ""
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _num(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_pine(path: Path | None = PINE_FILE) -> dict[str, ParamMeta]:
    out: dict[str, ParamMeta] = {}
    if path is None or not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _INPUT_RE.match(line)
        if not m:
            continue
        name, typ, rest = m.groups()
        pos, kw = _kwargs(_split_args(rest))
        title = _unquote(kw.get("title") or (pos[1] if len(pos) > 1 else name))
        options = None
        if "options" in kw:
            options = [_unquote(o) for o in _split_args(kw["options"].strip()[1:-1])]
        out[name] = ParamMeta(
            name=name,
            type=typ,
            title=title,
            group=_unquote(kw.get("group")) or "⚙️ Ostatné",
            tooltip=_unquote(kw.get("tooltip")),
            options=options,
            min=_num(kw.get("minval")),
            max=_num(kw.get("maxval")),
            step=_num(kw.get("step")),
            inline=_unquote(kw.get("inline")) or None,
        )
    return out


def _group_order(path: Path | None = PINE_FILE) -> list[str]:
    """Skupiny v poradí, v akom sa objavujú v Pine — tak ich radí aj TradingView."""
    order: list[str] = []
    if path is not None and path.exists():
        for m in _GROUP_ORDER_RE.finditer(path.read_text(encoding="utf-8")):
            if m.group(1) not in order:
                order.append(m.group(1))
    order.append("⚙️ Ostatné")
    order.append(PORT_GROUP)
    return order


def param_metadata(spec: StrategySpec | str | None = None) -> list[dict[str, Any]]:
    """Jeden záznam na každé pole configu stratégie, v poradí Pine skupín.

    Default je Pine default (= `config_cls()`), nie hodnota z profilu — profil sa
    do formulára načíta zvlášť a formulár zvýrazní odchýlky. Bez argumentu IBS.
    """
    if spec is None:
        spec = IBS_SPEC
    elif isinstance(spec, str):
        spec = get_spec(spec)
    cls = spec.config_cls
    pine = _parse_pine(spec.pine_path)
    defaults = cls()
    cfg_fields = {f.name: f for f in fields(cls)}
    order = {g: i for i, g in enumerate(_group_order(spec.pine_path))}

    metas: list[ParamMeta] = []
    for name in cfg_fields:
        if name in spec.removed_inputs:
            continue
        default = getattr(defaults, name)
        if name in pine:
            meta = pine[name]
        else:
            extra = spec.port_only_meta.get(name, {})
            meta = ParamMeta(
                name=name,
                type="string",
                title=extra.get("title", name),
                group=PORT_GROUP,
                tooltip=extra.get("tooltip", ""),
            )
        # typ podľa configu, nie podľa Pine — SizeSpec a enumy sú iné
        if isinstance(default, SizeSpec):
            meta.type = "size"
            meta.pine_unit = cls.SIZE_FIELDS[name]
            meta.default = default.value if default.unit == meta.pine_unit else default.to_json()
        elif isinstance(default, bool):
            meta.type = "bool"
            meta.default = default
        elif isinstance(default, int):
            meta.type = "int"
            meta.default = default
        elif isinstance(default, float):
            meta.type = "float"
            meta.default = default
        elif default is None:
            # voliteľné pole (napr. tickDollarValue): typ podľa Pine vstupu, inak text
            meta.type = meta.type if meta.type in ("int", "float", "bool", "string") else "string"
            meta.default = None
        else:
            v = getattr(default, "value", default)
            meta.type = "color" if meta.type == "color" else "string"
            meta.default = v
        if name in cls.CONSTRAINTS and meta.min is None:
            meta.min, meta.max = cls.CONSTRAINTS[name]
        if name in spec.param_notes:
            meta.note = spec.param_notes[name]
        if name in cls.PORT_ONLY_FIELDS:
            meta.group = PORT_GROUP
        metas.append(meta)

    by_name = {m.name: m for m in metas}
    for feat in spec.features:
        for name in feat["params"]:
            by_name[name].depends_on = list(feat["switches"])
        if feat.get("show"):
            by_name[feat["switches"][0]].show_param = feat["show"]

    metas.sort(key=lambda m: (order.get(m.group, 999), 0))
    return [m.to_dict() for m in metas]


def strategy_meta(spec: StrategySpec) -> dict[str, Any]:
    """Balík pre prehliadač: metadáta polí a Pine defaulty jednej stratégie."""
    return {"params": param_metadata(spec), "defaults": spec.config_cls().to_dict()}


def groups(spec: StrategySpec | str | None = None) -> list[str]:
    seen: list[str] = []
    for m in param_metadata(spec):
        if m["group"] not in seen:
            seen.append(m["group"])
    return seen
