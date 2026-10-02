"""Popisy parametrov FVG POLARITY pre formulár webapp."""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🟪 FVG"
_G1 = "🚀 Vstup"
_G2 = "🛡️ Stop a ciel"
_G3 = "💰 Riziko"
_G4 = "🎨 Vizualizacia"
_G5 = "🧩 Rozšírenia portu"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5)

PARAMS: dict[str, dict[str, Any]] = {
    "fvgMinSize": dict(
        group=_G0, title="FVG: min. velkost (body)",
        tooltip="Najmensia vyska medzery v bodoch ceny, ktora sa obchoduje; 0 = kazdy FVG.",
    ),
    "fvgMaxSize": dict(
        group=_G0, title="FVG: max. velkost (body)",
        tooltip="Najvacsia vyska medzery v bodoch ceny; 0 = bez obmedzenia.",
    ),
    "tradeDirection": dict(
        group=_G1, title="Smer obchodov",
        tooltip="Both = long po medvedom FVG (medzera nad cenou) aj short po bycom (medzera pod cenou).",
    ),
    "slPoints": dict(
        group=_G2, title="SL (body)",
        tooltip="Stop loss v bodoch ceny od vstupu. Zadanie: 20 bodov (MNQ).",
    ),
    "tpLevel": dict(
        group=_G2, title="TP v medzere",
        tooltip="near = prvy dotyk FVG (blizsia hrana medzery, zadanie); mid = stred medzery; far = vzdialenejsia "
                "hrana (medzera sa cela vyplni).",
    ),
    "atrLen": dict(
        group=_G2, title="Dlzka ATR",
        tooltip="ATR grafu - pouzije sa, len ked je niektora velkost zadana v jednotke atr.",
    ),
    "riskDollar": dict(
        group=_G3, title="Riziko na obchod ($)",
        tooltip="Kolko dolarov stoji jeden stop; velkost pozicie sa dopocita zo SL.",
    ),
    "showFvg": dict(
        group=_G4, title="Kreslit FVG",
        tooltip="Box FVG v grafe behu (aj tie, ktore sa neobchodovali, lebo bezal obchod).",
    ),
    "tickDollarValue": dict(
        group=_G5, title="Hodnota ticku ($)",
        tooltip="Kolko dolarov je jeden tick (MNQ 0,25 bodu = 0,50 $).",
    ),
    "legacyPineSizing": dict(
        group=_G5, title="Pine vzorec velkosti",
        tooltip="Doslovny Pine vzorec velkosti pozicie (int + max 1). Len na porovnanie s TradingView.",
    ),
    "minSlDistance": dict(
        group=_G5, title="Min. vzdialenost SL",
        tooltip="Obchod s tesnejsim stopom sa preskoci. 0 = vypnute.",
    ),
    "leverage": dict(
        group=_G5, title="Paka (Freqtrade)",
        tooltip="Paka vo Freqtrade futures. Na MultiCharts bez ucinku.",
    ),
}

# ---- typ vstupu market / limit (spoločný pre stratégie mimo IBS, `tradebot.core.entry_order`) ---- #
from tradebot.core.entry_confirm import entry_confirm_params  # noqa: E402
from tradebot.core.entry_order import entry_order_params  # noqa: E402

_GE = "🧾 Typ vstupu (market / limit)"
GROUPS = GROUPS + (_GE,)
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
