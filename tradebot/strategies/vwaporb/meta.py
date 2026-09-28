"""Metadáta VWAP ORB pre webapp — vrstvy ORB + VWAP."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer
from ..orb.meta import FEATURES as ORB_FEATURES, KIND_TITLES as ORB_KIND_TITLES, LAYERS as ORB_LAYERS
from ..orb.meta import PARAM_NOTES as ORB_PARAM_NOTES

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    **ORB_PARAM_NOTES,
    "vwapAnchor": "S kotvou 9:30 NY je VWAP na konci rangu vždy vnútri neho (je to priemer cien "
                  "rangu) — za range sa dostane, až keď cena drží za ním dosť dlho.",
    "exitMode": "Pri 'vwap' je cieľ technicky 100R — v analytike je preto plánované RR 100, "
                "skutočný výsledok určuje VWAP alebo stop.",
    "entryWindowMinutes": "Pri VWAP ORB je default 0 (do konca seansy): VWAP sa za range dostane "
                          "často až neskôr počas dňa.",
}

FEATURES: list[dict[str, Any]] = [*ORB_FEATURES, {"switches": ["showVwap"], "params": []},
                                  {"switches": ["vwapStop"], "params": ["vwapStopAtr"]},
                                  {"switches": ["vwapTp"], "params": ["vwapTpAtr"]}]

LAYERS: tuple[ChartLayer, ...] = (
    *ORB_LAYERS[:2],
    ChartLayer("vwap", "VWAP", ("vo_vwap",), "#a855f7"),
    *ORB_LAYERS[2:],
)

KIND_TITLES: dict[str, str] = {**ORB_KIND_TITLES, "vo_vwap": "VWAP"}
