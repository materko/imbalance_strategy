"""Popisy parametrov VWAP ORB (C# jadro) — zhodné s VWAP ORB, bez stopu posúvaného s VWAP (C# ho nemá)."""

from ..vwaporb.params import GROUPS
from ..vwaporb.params import PARAMS as _PARAMS
from .meta import INERT_INPUTS

_NEMA = " V C# jadre nie je: zapnute beh odmietne - pouzi strategiu 'vwaporb' (Python)."

PARAMS = {k: v for k, v in _PARAMS.items() if k not in INERT_INPUTS}
PARAMS["vwapStop"] = {**PARAMS["vwapStop"], "title": "SL na dotyk VWAP (v C# nie je)",
                      "tooltip": PARAMS["vwapStop"]["tooltip"] + _NEMA}
PARAMS["vwapTp"] = {**PARAMS["vwapTp"], "title": "TP na cross VWAP (v C# nie je)",
                    "tooltip": PARAMS["vwapTp"]["tooltip"] + _NEMA}

__all__ = ["GROUPS", "PARAMS"]
