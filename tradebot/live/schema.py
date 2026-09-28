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
    "SCHEMA", "KINDS", "REQUIRED", "PLATFORMS",
    "instance_id", "parse_line", "validate", "SchemaError",
]

SCHEMA = 1

PLATFORMS = ("ninjatrader", "mt5")

#: Druh → polia, ktoré musí mať okrem spoločných `seq`, `t`, `k`.
REQUIRED: dict[str, tuple[str, ...]] = {
    "hello": ("schema", "platform", "account", "symbol", "tf", "strategy", "session"),
    "bar": ("bt", "o", "h", "l", "c", "v", "ready"),
    "order": ("bt", "ready", "a", "id"),
    "event": ("bt", "z", "f", "to"),
    "draw": ("bt", "d"),
    "fill": ("ft", "id", "side", "price", "qty", "ready"),
    "stat": ("stats",),
    "note": ("text",),
    "bye": (),
}
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
    if kind == "fill" and ev["side"] not in ("in", "out"):
        raise SchemaError(f"fill: side musí byť in/out, je {ev['side']!r}")
    if kind == "draw" and not isinstance(ev["d"], list):
        raise SchemaError("draw: d musí byť pole kresieb")
    return ev
