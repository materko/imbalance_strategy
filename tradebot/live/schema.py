"""Schéma udalostí live telemetrie (`schema: 1`) — zrkadlo `csharp/TradeBot.Core/Live.cs`.

Riadok spoolu je JSON objekt `{"seq", "t", "k", …}`; druhy a ich polia sú v docs/LIVE.md.
Tu je to, čo potrebuje Python strana: názvy druhov, povinné polia na validáciu (testy,
odmietnutie zjavne rozbitého riadku pri príjme) a `instance_id`, ktoré musí dať to isté,
čo `LiveSpool.InstanceId` v C#.
"""

from __future__ import annotations

import json
import re
from typing import Any

__all__ = [
    "SCHEMA", "KINDS", "REQUIRED", "PLATFORMS", "CONTROL_MODES", "ORDER_ACTIONS",
    "instance_id", "parse_line", "validate", "SchemaError",
]

SCHEMA = 1

PLATFORMS = ("ninjatrader", "mt5")

#: Druh → polia, ktoré musí mať okrem spoločných `seq`, `t`, `k`.
REQUIRED: dict[str, tuple[str, ...]] = {
    "hello": ("schema", "platform", "account", "symbol", "tf", "strategy", "session"),
    "bar": ("bt", "o", "h", "l", "c", "v", "ready"),
    #: `a` entry/cancel/close sú zámery enginu (`OrderIntent.WriteJson`); `modify` je adaptér
    #: (posun SL/TP na pracujúcom ordere, napr. trailing): `p{sl,tp}` (null = nemenené), `r` dôvod.
    "order": ("bt", "ready", "a", "id"),
    "event": ("bt", "z", "f", "to"),
    "draw": ("bt", "d"),
    "fill": ("ft", "id", "side", "price", "qty", "ready"),
    "stat": ("stats",),
    "note": ("text",),
    #: Adaptér potvrdzuje, v akom režime beží (fáza 2, control súbor): `mode` enabled/paused/flatten,
    #: `profile` názov práve načítaného profilu, `source` odkiaľ (control/default).
    "control": ("mode",),
    "bye": (),
}
CONTROL_MODES = ("enabled", "paused", "flatten")
ORDER_ACTIONS = ("entry", "cancel", "close", "modify")
KINDS = tuple(REQUIRED)

_BAD = re.compile(r"[^A-Za-z0-9._-]")


class SchemaError(ValueError):
    """Riadok nie je platná udalosť telemetrie."""


def instance_id(platform: str, account: str, symbol: str, tf_minutes: int, strategy: str) -> str:
    """`<platform>_<account>_<symbol>_<tf>m_<strategy>`, znaky mimo `[A-Za-z0-9._-]` → `-`.

    Musí sedieť s `LiveSpool.InstanceId` v C# — je to názov adresára spoolu a kľúč inštancie
    v hube aj webapp.
    """
    parts = (platform, account, symbol, f"{int(tf_minutes)}m", strategy)
    return "_".join(_BAD.sub("-", str(p or "")) for p in parts)


def instance_symbol(platform: str, symbol: str) -> str:
    """Symbol tak, ako ho platforma dá do id inštancie (`LiveSpool.InstanceId`).

    NinjaTrader: adaptér aj AddOn používajú `Instrument.MasterInstrument.Name` (`MNQ`), kým
    nasadenie nesie celý názov inštrumentu `MNQ 12-26` (master + expirácia) — do id ide len
    časť pred prvou medzerou; inak by hub počítal `…_MNQ-12-26_…`, agent písal control súbor
    pod týmto menom a AddOn (spool `…_MNQ_…`) by ho nikdy nečítal. Ostatné platformy (MT5
    symboly medzery nemajú) sa nemenia.
    """
    text = str(symbol or "").strip()
    if str(platform or "").lower() == "ninjatrader":
        return text.split()[0] if text.split() else text
    return text


def parse_line(line: str | bytes) -> dict[str, Any]:
    """JSON riadok → udalosť; `SchemaError`, keď to nie je objekt alebo nesedí schéma."""
    try:
        ev = json.loads(line)
    except ValueError as exc:
        raise SchemaError(f"nie je JSON: {exc}") from None
    validate(ev)
    return ev


def validate(ev: Any) -> dict[str, Any]:
    """Skontroluje spoločné polia a povinné polia druhu; vráti udalosť späť."""
    if not isinstance(ev, dict):
        raise SchemaError("udalosť musí byť JSON objekt")
    for key in ("seq", "t", "k"):
        if key not in ev:
            raise SchemaError(f"chýba pole {key!r}")
    if not isinstance(ev["seq"], int) or isinstance(ev["seq"], bool) or ev["seq"] < 1:
        raise SchemaError(f"seq musí byť celé číslo od 1, je {ev['seq']!r}")
    if not isinstance(ev["t"], int) or isinstance(ev["t"], bool):
        raise SchemaError(f"t musí byť ms epoch (celé číslo), je {ev['t']!r}")
    kind = ev["k"]
    if kind not in REQUIRED:
        raise SchemaError(f"neznámy druh udalosti {kind!r}")
    missing = [f for f in REQUIRED[kind] if f not in ev]
    if missing:
        raise SchemaError(f"{kind}: chýbajú polia {missing}")
    if kind == "hello":
        if ev["schema"] != SCHEMA:
            raise SchemaError(f"hello: schéma {ev['schema']!r}, čítam {SCHEMA}")
        if ev["platform"] not in PLATFORMS:
            raise SchemaError(f"hello: neznáma platforma {ev['platform']!r}")
    if kind == "order" and ev["a"] not in ORDER_ACTIONS:
        raise SchemaError(f"order: a musí byť {'/'.join(ORDER_ACTIONS)}, je {ev['a']!r}")
    if kind == "fill" and ev["side"] not in ("in", "out"):
        raise SchemaError(f"fill: side musí byť in/out, je {ev['side']!r}")
    if kind == "draw" and not isinstance(ev["d"], list):
        raise SchemaError("draw: d musí byť pole kresieb")
    if kind == "control" and ev["mode"] not in CONTROL_MODES:
        raise SchemaError(f"control: mode musí byť {'/'.join(CONTROL_MODES)}, je {ev['mode']!r}")
    return ev
