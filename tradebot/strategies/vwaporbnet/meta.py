"""Metadáta VWAP ORB (C# jadro) pre webapp — vrstvy grafu, závislosti prepínačov; zhodné s VWAP ORB.

Bez stopu posúvaného s VWAP: C# jadro ho nemá — prepínače `vwapStop`/`vwapTp` formulár ukazuje s popisom, že ich
C# nemá (zapnuté config odmietne), a ich rezervy (`vwapStopAtr`, `vwapTpAtr`) nečíta nič, preto sú inertné.
"""

from ..vwaporb.meta import FEATURES as _FEATURES
from ..vwaporb.meta import INTENTIONAL_DEFAULT_DIFFS, KIND_TITLES, LAYERS, REMOVED_INPUTS
from ..vwaporb.meta import PARAM_NOTES as _PARAM_NOTES

#: Rezervy stopu posúvaného s VWAP — C# jadro ho nemá, takže ich nič nečíta.
INERT_INPUTS: frozenset[str] = frozenset({"vwapStopAtr", "vwapTpAtr"})

FEATURES = [f for f in _FEATURES if not set(f.get("params", [])) & INERT_INPUTS]

PARAM_NOTES = {
    **{k: v for k, v in _PARAM_NOTES.items() if k not in INERT_INPUTS},
    "vwapStop": "C# jadro stop posúvaný s VWAP nemá — zapnutý config odmietne (použi stratégiu 'vwaporb').",
    "vwapTp": "C# jadro TP na cross VWAP nemá — zapnutý config odmietne (použi stratégiu 'vwaporb').",
}

__all__ = ["FEATURES", "INERT_INPUTS", "INTENTIONAL_DEFAULT_DIFFS", "KIND_TITLES", "LAYERS", "PARAM_NOTES",
           "REMOVED_INPUTS"]
