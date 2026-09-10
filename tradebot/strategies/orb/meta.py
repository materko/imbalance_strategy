"""Metadáta ORB pre webapp — vrstvy grafu, závislosti prepínačov, polia mimo Pine."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "slRangePct": "Platí len pri umiestnení SL `range_pct`. 50 % je to isté ako `mid`, "
                  "100 % to isté ako `opposite`.",
    "measuredMult": "Klasický measured move: výška rangu premietnutá za miesto prerazenia.",
    "minRangePct": "Merania na indexoch: pod ~0,3 % šírky dominujú falošné prerazenia.",
    "entryWindowMinutes": "Prerazenia neskôr než 60–90 min od otvorenia výrazne zaostávajú.",
    "sessionMode": "New York a Londýn sa prekrývajú (NY 9:30 = Londýn 14:30). Pri oboch "
                   "zapnutých sa nová pozícia neotvorí, kým je iná otvorená.",
}

#: Prepínač -> podnastavenia, ktoré sa vo formulári zbalia pod neho.
FEATURES: list[dict[str, Any]] = [
    {"switches": ["useVolumeFilter"], "params": ["volSmaLen", "volMultiplier"]},
    {"switches": ["enableTrailing"], "params": ["trailActivationR", "trailOffsetR"]},
    {"switches": ["showRange"], "params": []},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("range", "Opening range", ("orb_box",), "#3b82f6"),
    ChartLayer("levels", "Hranice rangu", ("orb_high", "orb_low"), "#6366f1"),
    ChartLayer("entries", "Vstupy", ("orb_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "orb_box": "Opening range",
    "orb_high": "ORB high",
    "orb_low": "ORB low",
    "orb_entry": "Vstup (prerazenie)",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
