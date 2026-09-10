"""Metadáta stratégie tržnej štruktúry pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

#: Čo z parametra nie je vidieť na jeho titulku — hlavne to, kedy vôbec platí.
PARAM_NOTES: dict[str, str] = {
    "rrRatio": "Platí len pri exitMode = rr. Pri exitMode = structure obchod pevný cieľ nemá.",
    "slBuffer": "Platí len pri slMode = swing.",
    "slAtrMult": "Platí pri slMode = atr — a ako záloha vždy, keď potvrdený swing v protismere "
                 "ešte nie je alebo by stop vyšiel na zlú stranu vstupu (typicky pri sweep vstupe).",
    "maxBars": "Limit je v BAROCH grafu, nie v čase: na 15m znamená to isté číslo päťkrát dlhší "
               "obchod než na 3m.",
    "swingRight": "Zároveň to je oneskorenie: swing je potvrdený až toľkoto barov po tom, čo nastal, "
                  "a skôr o ňom stratégia nevie ani pri kreslení.",
}

#: Závislosti prepínač -> podnastavenia. Hodiny okna majú zmysel len so zapnutou seansou;
#: `exitMode`/`slMode` sú enumy, nie prepínače, takže ich formulár skryť nevie — čo kedy
#: platí, je preto v `PARAM_NOTES`.
FEATURES: list[dict[str, Any]] = [
    {"switches": ["useSession"], "params": ["sessionTZ", "sessionStartH", "sessionEndH"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("session", "Obchodné okno", ("session",), "#6366f1"),
    ChartLayer("swings", "Potvrdené swingy a úrovne", ("st_swing_high", "st_swing_low", "st_level"), "#334155"),
    ChartLayer("events", "BOS / CHoCH", ("st_bos", "st_choch"), "#d97706"),
    ChartLayer("entries", "Vstupy", ("st_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "st_swing_high": "Potvrdený swing high", "st_swing_low": "Potvrdený swing low",
    "st_level": "Referenčná úroveň", "st_bos": "BOS", "st_choch": "CHoCH",
    "st_entry": "Vstup (štruktúra)", "tp_box": "TP box", "sl_box": "SL box",
    "entry": "Vstup", "exit": "Výstup", "session": "Obchodné okno",
}
