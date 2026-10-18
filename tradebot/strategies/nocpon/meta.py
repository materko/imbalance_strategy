"""Metadáta NOC + PONDELOK pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "nightExitH": "Meranie MNQ 2019–2026: výstup 23:00 / 3:00 / 9:30 → PF 1,44 / 1,47 / 1,34 (s pondelkom).",
    "nightEntryH": "Vstup 15:30–15:55 dáva PF 1,33–1,35 (len noc).",
    "smaLen": "SMA 50–200 dní: PF 1,32–1,38; bez filtra 1,24 a rok 2022 v strate.",
    "skipRoll": "Dáta MNQ sú front-month bez back-adjustmentu — noc rollu má umelý skok.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useNight"], "params": ["nightEntryH", "nightEntryM", "nightExitH", "nightExitM"]},
    {"switches": ["useMonday"], "params": ["monEntryH", "monEntryM", "monExitH", "monExitM"]},
    {"switches": ["useTrend"], "params": ["smaLen", "closeRefH", "closeRefM"]},
    {"switches": ["skipRoll"], "params": ["rollFromDay", "rollToDay"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("sma", "SMA denných zavretí", ("np_sma",), "#a78bfa"),
    ChartLayer("entries", "Vstupy (noc / pondelok)", ("np_entry",), "#10b981"),
    ChartLayer("tpsl", "Obchod do termínu výstupu", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "np_sma": "SMA denných zavretí",
    "np_entry": "Vstup",
    "tp_box": "Obchod do termínu výstupu (1 R na orientáciu)",
    "sl_box": "Stop / poistka",
    "entry": "Vstup",
    "exit": "Výstup",
}
