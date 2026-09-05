"""Metadáta parametrov pre formulár — z Pine skriptu, nie ručne.

Formulár má ukazovať to isté, čo panel nastavení v TradingView: rovnaké skupiny,
rovnaké titulky, rovnaké tooltipy. Všetko to v Pine skripte už je, takže sa parsuje
odtiaľ (`imbalance_strategy_FULL.pine`) a k tomu sa pridajú polia, ktoré Pine nemá
(`PORT_ONLY_FIELDS`). Keď niekto v Pine zmení tooltip, formulár ho zmení tiež.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from ..core import IBSConfig
from ..core.config import CONSTRAINTS, PORT_ONLY_FIELDS, SIZE_FIELDS
from ..core.types import SizeSpec

REPO = Path(__file__).resolve().parents[2]
PINE_FILE = REPO / "imbalance_strategy_FULL.pine"

#: Vstupy, ktoré sa neportujú (viď `ibs/tests/test_pine_parity.py`).
REMOVED_INPUTS = {"pmtToken", "pmtAccountId", "pmtStratName", "pmtMarketOrderType", "trailFreqPct"}

PORT_GROUP = "🧩 Rozšírenia portu (nie sú v Pine)"

#: Metadáta polí, ktoré Pine nemá — ručne, lebo niet odkiaľ ich parsovať.
_PORT_ONLY_META: dict[str, dict[str, Any]] = {
    "atrLen": dict(
        title="ATR dĺžka pre jednotku „atr“",
        tooltip="Dĺžka ATR na grafovom TF, z ktorej sa prepočítavajú parametre zadané v jednotke atr. "
        "V Pine ATR nie je; slúži na prenos prahov medzi nástrojmi s inou cenovou škálou.",
    ),
    "legacyPineSizing": dict(
        title="Pine sizing (1 kontrakt/BTC, ako TradingView)",
        tooltip="Doslovný Pine vzorec veľkosti pozície vrátane int() a max(1, …) — na BTC vždy 1 BTC bez ohľadu "
        "na maxLossDollar. Zapnúť len na porovnanie s TradingView. Vyžaduje tickDollarValue.",
    ),
    "leverage": dict(
        title="Páka",
        tooltip="Páka vo Freqtrade futures. Nemení edge, len umožní otvoriť pozíciu z risk-based sizingu, "
        "ktorá by sa inak na účet nezmestila (stake by sa orezal a riziko by bolo menšie než maxLossDollar).",
    ),
    "minSlDistance": dict(
        title="Min. vzdialenosť SL od vstupu",
        tooltip="Obchod s tesnejším SL sa preskočí (SKIP: SL PRILIS TESNY). Poplatok je percento z nominálu, "
        "zisk rastie s R — tesné SL majú najhorší pomer edge k poplatku. 0 = vypnuté. "
        "Odporúčaná jednotka pct (0,20 % ceny), viď docs/OPTIMALIZACIA_2026-09-05.md.",
    ),
}

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


def _parse_pine(path: Path = PINE_FILE) -> dict[str, ParamMeta]:
    out: dict[str, ParamMeta] = {}
    if not path.exists():
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


def _group_order(path: Path = PINE_FILE) -> list[str]:
    """Skupiny v poradí, v akom sa objavujú v Pine — tak ich radí aj TradingView."""
    order: list[str] = []
    if path.exists():
        for m in _GROUP_ORDER_RE.finditer(path.read_text(encoding="utf-8")):
            if m.group(1) not in order:
                order.append(m.group(1))
    order.append("⚙️ Ostatné")
    order.append(PORT_GROUP)
    return order


def param_metadata() -> list[dict[str, Any]]:
    """Jeden záznam na každé pole `IBSConfig`, v poradí Pine skupín.

    Default je Pine default (= `IBSConfig()`), nie hodnota z profilu — profil sa
    do formulára načíta zvlášť a formulár zvýrazní odchýlky.
    """
    pine = _parse_pine()
    defaults = IBSConfig()
    cfg_fields = {f.name: f for f in fields(IBSConfig)}
    order = {g: i for i, g in enumerate(_group_order())}

    metas: list[ParamMeta] = []
    for name in cfg_fields:
        if name in REMOVED_INPUTS:
            continue
        default = getattr(defaults, name)
        if name in pine:
            meta = pine[name]
        else:
            extra = _PORT_ONLY_META.get(name, {})
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
            meta.pine_unit = SIZE_FIELDS[name]
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
            meta.type = "float" if name == "tickDollarValue" else "string"
            meta.default = None
        else:
            v = getattr(default, "value", default)
            meta.type = "color" if meta.type == "color" else "string"
            meta.default = v
        if name in CONSTRAINTS and meta.min is None:
            meta.min, meta.max = CONSTRAINTS[name]
        if name == "state4MaxBars":
            meta.note = "Pine tento parameter nikde nepoužíva."
        if name in PORT_ONLY_FIELDS:
            meta.group = PORT_GROUP
        metas.append(meta)

    metas.sort(key=lambda m: (order.get(m.group, 999), 0))
    return [m.to_dict() for m in metas]


def groups() -> list[str]:
    seen: list[str] = []
    for m in param_metadata():
        if m["group"] not in seen:
            seen.append(m["group"])
    return seen
