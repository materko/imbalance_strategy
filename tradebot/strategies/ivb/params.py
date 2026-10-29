"""Popisy parametrov IVB pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🕘 Seansa (New York, HHMM)"
_G1 = "📏 Stlačený IB a objem"
_G2 = "🛡️ Stop, cieľ a koniec dňa"
_G3 = "💰 Veľkosť"
_G4 = "🎨 Vizualizácia"
_G5 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "sessionStart": dict(group=_G0, title="Začiatok IB (HHMM)", inline="ib", tooltip="Predloha: 930 = 9:30 New York."),
    "sessionEnd": dict(group=_G0, title="Koniec IB (HHMM)", inline="ib", tooltip="Predloha: 1000 — IB = prvých 30 min."),
    "entryWindowEnd": dict(group=_G0, title="Koniec okna vstupu (HHMM)", tooltip="Vstupy od konca IB do tohto času."),
    "direction": dict(group=_G0, title="Smer", options=[0, 1, 2], tooltip="0 = oba, 1 = len long, 2 = len short."),
    "maxContractionRatio": dict(group=_G1, title="IB / priemer IB najviac", inline="cr", step=0.05,
                                tooltip="Stlačený deň: dnešný IB voči priemeru posledných IB."),
    "minContractionRatio": dict(group=_G1, title="najmenej", inline="cr", step=0.01, tooltip="0 = bez dolnej hranice."),
    "ibRangeLookback": dict(group=_G1, title="Priemer IB z posledných (dní)",
                            tooltip="Predloha zapisuje IB na baroch 10:00–10:04 — na 1m grafe 5× za deň."),
    "volSurgeMult": dict(group=_G1, title="Objem baru aspoň (× priemer)", step=0.1,
                         tooltip="Priemer posledných objemov RTH (9:30–16:00), vrátane tohto baru."),
    "volAvgBars": dict(group=_G1, title="Priemer objemu z (barov)", tooltip="Bary RTH, aj z predošlých dní."),
    "maxTradesPerDay": dict(group=_G1, title="Max pokusov za deň",
                            tooltip="Predloha ráta pokus pri splnenom IB a objeme aj bez prierazu."),
    "atrPeriod": dict(group=_G2, title="ATR (Wilder)", tooltip="Na grafe."),
    "slAtrMult": dict(group=_G2, title="Stop (× ATR)", inline="sl", step=0.5, tooltip="Od zavretia signálneho baru."),
    "tpAtrMult": dict(group=_G2, title="Cieľ (× ATR)", inline="sl", step=0.5, tooltip="Od zavretia signálneho baru."),
    "flattenEod": dict(group=_G2, title="Zavrieť na konci dňa", tooltip="Predloha: vypnuté — pozícia môže ísť cez noc."),
    "eodFlatten": dict(group=_G2, title="Čas zavretia (HHMM)", tooltip="New York."),
    "riskDollar": dict(group=_G3, title="Riziko na obchod ($)",
                       tooltip="Predloha: 2 % účtu (`risk_pct`); tu v $ pri vypnutom pevnom počte."),
    "drawIbZone": dict(group=_G4, title="Kresliť IB", tooltip="Zóna 9:30–10:00."),
    "leverage": dict(group=_G5, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
