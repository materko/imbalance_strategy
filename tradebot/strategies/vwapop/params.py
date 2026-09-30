"""Popisy parametrov VWAP OP pre formulár webapp.

Zdroj pravdy pre ľudské názvy a vysvetlenia. Rozsahy a defaulty sú v `config.py`
(`CONSTRAINTS` a defaulty dataclass).
"""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

_G1 = "📈 VWAP / Drift (HTF)"
_G2 = "🚀 Vstupy"
_G3 = "🛡️ Risk / výstupy"
_G4 = "🎨 Vzhľad"
_G5 = "🧩 Rozšírenia portu"

GROUPS: tuple[str, ...] = (_G1, _G2, _G3, _G4, _G5)

PARAMS: dict[str, dict[str, Any]] = {
    # ---- 📈 VWAP / Drift (HTF) ----------------------------------------- #
    "htf": dict(
        group=_G1, title="VWAP timeframe",
        tooltip="Timeframe, z ktorého sa počíta VWAP aj drift (Pine input.timeframe, napr. '15' pre "
                "15-minútové sviečky). Graf musí mať TF, ktorým sa toto číslo delí (1m, 3m, 5m, 15m).",
    ),
    "rthSess": dict(
        group=_G1, title="RTH seansa",
        tooltip="Okno seansy (HHMM-HHMM, America/New_York), v ktorom sa VWAP počíta a od ktorého sa "
                "nuluje každý deň. Predvolene 9:30-16:00 (cash seansa).",
    ),
    "driftLen": dict(
        group=_G1, title="Drift za periód",
        tooltip="Drift = o koľko sa VWAP zmenil za toľkoto posledných HTF periód (napr. pri 15m a 2 je "
                "to posledná pol hodina).",
    ),
    "driftAtr": dict(
        group=_G1, title="Min. sklon VWAP (ATR HTF)",
        tooltip="Koľko sa VWAP musí za 'Drift za periód' pohnúť, aby to bol jasný smer dňa — v násobkoch "
                "ATR **toho istého HTF**, nie ATR grafu. Pod prahom je bias 0 (na rozdiel od VWAP Session "
                "1.0 sa tu smer dňa nedrží — prepočíta sa nanovo na každom bare).",
    ),
    "needSide": dict(
        group=_G1, title="Close HTF na strane trendu",
        tooltip="Aby drift platil, musí aj close poslednej uzavretej HTF sviečky byť nad VWAP (long) "
                "alebo pod ním (short). Vypnuté = stačí sklon.",
    ),
    # ---- 🚀 Vstupy ------------------------------------------------------- #
    "tolAtr": dict(
        group=_G2, title="Tolerancia dotyku VWAP (ATR grafu)",
        tooltip="Pullback = low baru (short: high) príde k VWAP bližšie než táto tolerancia — v násobkoch "
                "ATR grafu (nie HTF). Vstup je market na zavretí toho istého baru.",
    ),
    "needClose": dict(
        group=_G2, title="Sviečka musí zavrieť na strane trendu",
        tooltip="Zapnuté = bar, ktorý sa dotkol VWAP, musí aj zavrieť späť na strane driftu, inak vstup "
                "nie je (aj keď sa dotkol).",
    ),
    "firstOnly": dict(
        group=_G2, title="Len prvý pullback za deň",
        tooltip="V danom smere sa obchoduje len prvý pullback dňa — aj keď sa neobchodoval (napr. mimo "
                "okna), smer je na zvyšok dňa uzamknutý.",
    ),
    "maxTrades": dict(
        group=_G2, title="Max. obchodov za deň",
        tooltip="Strop na počet vstupov za deň, oba smery spolu.",
    ),
    "tradeWin": dict(
        group=_G2, title="Okno pre vstupy",
        tooltip="Mimo tohto okna (HHMM-HHMM, America/New_York) sa nevstupuje, aj keď signál sedí.",
    ),
    "allowLong": dict(group=_G2, title="Povoliť LONG", tooltip="Vypnuté = long signály sa ignorujú."),
    "allowShort": dict(group=_G2, title="Povoliť SHORT", tooltip="Vypnuté = short signály sa ignorujú."),
    # ---- 🛡️ Risk / výstupy ------------------------------------------------ #
    "slAtr": dict(
        group=_G3, title="SL za VWAP (ATR grafu)",
        tooltip="Stop je vždy VWAP ∓ toľkoto ATR grafu (nie za extrém pullbacku) — pevný po celý obchod, "
                "kým ho neposunie breakeven.",
    ),
    "rr": dict(
        group=_G3, title="Take profit (R)", step=0.25,
        tooltip="Cieľ = toľkoto násobkov vzdialenosti stopu.",
    ),
    "useBE": dict(
        group=_G3, title="Breakeven po +1R",
        tooltip="Zapnuté = len čo zisk dosiahne +1R, SL sa raz posunie na cenu vstupu a tam zamrzne — "
                "nie je to kontinuálny trailing.",
    ),
    "closeEOD": dict(
        group=_G3, title="Zatvoriť na konci seansy",
        tooltip="Vypnuté (default) = otvorená pozícia ostáva aj po konci seansy, aj cez noc — ukončí ju "
                "len SL alebo TP. Zapnuté = zatvorí sa v okne 'Čas zatvorenia'.",
    ),
    "flatTime": dict(
        group=_G3, title="Čas zatvorenia",
        tooltip="Okno (HHMM-HHMM, America/New_York), v ktorom sa pozícia zatvorí, ak je 'Zatvoriť na "
                "konci seansy' zapnuté.",
    ),
    # ---- 🎨 Vzhľad --------------------------------------------------------- #
    "showCross": dict(
        group=_G4, title="Kresliť VWAP",
        tooltip="Čiara VWAP v grafe behu, farbená driftom.",
    ),
    "colUp": dict(group=_G4, title="Farba: drift hore", type="color"),
    "colDn": dict(group=_G4, title="Farba: drift dole", type="color"),
    "colFlat": dict(group=_G4, title="Farba: bez driftu", type="color"),
    # ---- 🧩 Rozšírenia portu ------------------------------------------------ #
    "riskDollar": dict(
        group=_G5, title="Riziko na obchod ($)",
        tooltip="Koľko dolárov stojí jeden stop; veľkosť pozície sa dopočíta zo vzdialenosti stopu. "
                "Pine má natvrdo 1 kontrakt — toto je rozšírenie portu.",
    ),
    "legacyPineSizing": dict(
        group=_G5, title="Pine veľkosť (1 kontrakt)",
        tooltip="Doslovná Pine veľkosť — vždy presne 1 kontrakt, bez ohľadu na riziko. Len na porovnanie "
                "s TradingView.",
    ),
    "minSlDistance": dict(
        group=_G5, title="Min. vzdialenosť SL",
        tooltip="Obchod s tesnejším stopom sa preskočí. 0 = vypnuté.",
    ),
    "leverage": dict(
        group=_G5, title="Páka (Freqtrade)",
        tooltip="Páka vo Freqtrade futures. Na MultiCharts bez účinku.",
    ),
}

# ---- typ vstupu market / limit (spoločný pre stratégie mimo IBS, `tradebot.core.entry_order`) ---- #
from tradebot.core.entry_order import entry_order_params  # noqa: E402

_GE = "🧾 Typ vstupu (market / limit)"
GROUPS = GROUPS + (_GE,)
PARAMS.update(entry_order_params(_GE))
