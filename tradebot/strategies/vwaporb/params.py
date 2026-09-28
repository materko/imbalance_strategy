"""Popisy parametrov VWAP ORB — ORB + skupina VWAP."""

from __future__ import annotations

from typing import Any

from ..orb.params import GROUPS as ORB_GROUPS, PARAMS as ORB_PARAMS

__all__ = ["GROUPS", "PARAMS"]

_GV = "📊 VWAP"

#: VWAP hneď za seansami — je to podmienka vstupu, nie filter navyše.
GROUPS: tuple[str, ...] = (ORB_GROUPS[0], _GV, *ORB_GROUPS[1:])

PARAMS: dict[str, dict[str, Any]] = {
    **ORB_PARAMS,
    "vwapAnchor": dict(
        group=_GV, title="Kotva VWAP",
        tooltip="Odkial sa VWAP pocita. 'ny_open' = od 9:30 New York (15:30 SEC), ako vo VWAP Session. "
                "'session' = klasicky seansovy VWAP CME futures od 18:00 NY. 'utc_day' = den od 00:00 UTC.",
    ),
    "vwapPeriod": dict(
        group=_GV, title="VWAP zo sviečok",
        tooltip="'15' = VWAP z 15-minutovych sviecok zlozenych z grafu (meni sa pri zatvoreni 15m sviecky). "
                "'chart' = priamo z barov grafu.",
    ),
    "vwapBreakAtr": dict(
        group=_GV, title="VWAP za rangom o (ATR)",
        tooltip="Signal je, ked VWAP prerazi nad high rangu (short: pod low) a zaroven je tam aj cena. "
                "Toto je, o kolko ATR musi byt VWAP za hranicou; 0 = staci byt za nou.",
    ),
    "closeBeyondVwap": dict(
        group=_GV, title="Cena aj za VWAP",
        tooltip="Zapnute = close musi byt aj nad VWAP (short: pod), nielen nad high rangu.",
    ),
    "showVwap": dict(
        group=_GV, title="Kreslit VWAP",
        tooltip="Ciara VWAP v grafe behu.",
    ),
}
