"""Metadáta FPC 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "contTP": "Video: eval účty 38 bodov cieľ, 25 bodov stop (1 : 1,5); pri otváracej sviečke nad 25 b. 76 / 50.",
    "minPct": "Video: na cieľ 100 bodov treba aspoň 80 bodov k férovej cene.",
    "maxLossRow": "Video: tri straty po sebe v seanse = trh sa nevracia, koniec.",
    "newsMode": "Video: v deň správy o 8:30 je férová cena tá pred správou; open 9:30 sa vtedy ignoruje.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useS1"], "params": ["s1H", "s1M", "s1Len"]},
    {"switches": ["useS2"], "params": ["s2H", "s2M", "s2Len", "pmFair"]},
    {"switches": ["useS3"], "params": ["s3H", "s3M", "s3Len"]},
    {"switches": ["useS4"], "params": ["s4H", "s4M", "s4Len"]},
    {"switches": ["newsMode"], "when": {"newsMode": ["auto", "always"]},
     "params": ["newsH", "newsM", "useNewsWin"]},
    {"switches": ["newsMode"], "when": {"newsMode": ["auto"]}, "params": ["newsMult", "newsAvgBars"]},
    {"switches": ["useCont"], "params": ["contWin", "useBias", "biasH", "contTP", "contSL", "bigBar"]},
    {"switches": ["useRev"], "params": ["tpMode", "revSL"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["fixed"]}, "params": ["revTP", "minPct"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["fair"]}, "params": ["minDist"]},
    {"switches": ["useBos"], "params": ["pivLen"]},
    {"switches": ["useCloseAfter"], "params": ["closeAfter"]},
    {"switches": ["useTrend"], "params": ["trendPts", "showVwap"]},
    {"switches": ["useMaxD"], "params": ["maxDist"]},
    {"switches": ["usePause"], "params": ["pauseMin"]},
    {"switches": ["useRevDel"], "params": ["revDelay"]},
    {"switches": ["useTests"], "params": ["minTests", "testTol"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("fair", "Férová cena a okno", ("fpc_fair", "fpc_window", "fpc_news"), "#f59e0b"),
    ChartLayer("zone", "Pásmo bez vstupu", ("fpc_zone",), "#f59e0b"),
    ChartLayer("vwap", "VWAP okna (filter trendu)", ("fpc_vwap",), "#06b6d4"),
    ChartLayer("signals", "Signály (D / S)", ("fpc_signal",), "#a855f7"),
    ChartLayer("entries", "Vstupy", ("fpc_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "fpc_window": "Obchodné okno",
    "fpc_fair": "Férová cena",
    "fpc_zone": "Pásmo bez vstupu okolo férovej ceny",
    "fpc_news": "Správa — cena pred ňou",
    "fpc_vwap": "VWAP okna",
    "fpc_signal": "Signál: D = displacement, S = prieraz štruktúry",
    "fpc_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
