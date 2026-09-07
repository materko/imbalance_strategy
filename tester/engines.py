"""Dva enginy, ktorými sa dá prehrať tá istá stratégia — a kde má každý dáta.

| engine | čo to je | dáta |
|---|---|---|
| `freqtrade` | Freqtrade backtest v podprocese, fill model Freqtradu | súbor na každý timeframe |
| `multicharts` | emulátor MultiCharts v tomto procese (`MCRunner` + broker podľa MultiCharts) | jeden 1m súbor, vyššie TF sa skladajú v pamäti |

Engine **nie je vlastnosť páru**. Krypto sa dá prehrať aj emulátorom a Dukascopy CFD aj
cez Freqtrade — práve na tom stojí porovnanie oboch ciest
([docs/FREQTRADE.md §G](../docs/FREQTRADE.md)). Obmedzuje to len to, aké dáta sú na disku,
a to hovorí `available()`.

Sviečky sú vždy `<dáta>/<zdroj>/<PÁR>-<TF>.feather`; zdroj je `InstrumentSpec.data_source`.
Freqtrade si pomenúva futures súbory príponou `-futures` a drží ich v podadresári, spot
nie — preto to rozlíšenie nižšie.
"""

from __future__ import annotations

from pathlib import Path

from tradebot.core.paths import FREQTRADE_DATA, FREQTRADE_DIR, MULTICHARTS_DATA
from tradebot.core.types import InstrumentSpec

__all__ = ["FREQTRADE", "MULTICHARTS", "ENGINES", "ENGINE_TITLES",
           "one_minute_file", "freqtrade_file", "freqtrade_datadir", "freqtrade_config",
           "available", "default_engine"]

FREQTRADE = "freqtrade"
MULTICHARTS = "multicharts"
ENGINES = (FREQTRADE, MULTICHARTS)

ENGINE_TITLES = {
    FREQTRADE: "Freqtrade",
    MULTICHARTS: "MultiCharts (emulátor)",
}

#: Zdroje, ktoré nie sú ccxt burza — Freqtrade ich vezme len cez vlastný config a `--datadir`.
_OFF_EXCHANGE = ("dukascopy",)


def _is_off_exchange(inst: InstrumentSpec) -> bool:
    return inst.data_source in _OFF_EXCHANGE


def freqtrade_datadir(inst: InstrumentSpec) -> Path:
    """Adresár, z ktorého číta Freqtrade — vždy podľa zdroja dát."""
    return FREQTRADE_DATA / inst.data_source


def freqtrade_file(inst: InstrumentSpec, timeframe: str) -> Path:
    """`BTC/USDT:USDT`, `3m` → `…/binance/futures/BTC_USDT_USDT-3m-futures.feather`."""
    base = inst.data_stem
    if _is_off_exchange(inst) or inst.is_spot:
        return freqtrade_datadir(inst) / f"{base}-{timeframe}.feather"
    return freqtrade_datadir(inst) / "futures" / f"{base}-{timeframe}-futures.feather"


def one_minute_file(inst: InstrumentSpec) -> Path:
    """1m sviečky pre emulátor. Dukascopy ich má v dátach MultiCharts, burzy vo Freqtrade."""
    if _is_off_exchange(inst):
        return MULTICHARTS_DATA / inst.data_source / f"{inst.data_stem}-1m.feather"
    return freqtrade_file(inst, "1m")


def freqtrade_config(inst: InstrumentSpec) -> Path:
    """Ktorý Freqtrade config na tento inštrument sedí.

    Spot má vlastný (`trading_mode: spot`), inak by Freqtrade pár ani nenašiel; symboly
    mimo ccxt búrz majú config s nosnou burzou a `allow_inactive`.
    """
    if _is_off_exchange(inst):
        return FREQTRADE_DIR / "config.dukascopy.json"
    if inst.is_spot:
        return FREQTRADE_DIR / "config.binance.spot.json"
    return FREQTRADE_DIR / "config.binance.json"


def available(inst: InstrumentSpec, timeframe: str = "3m") -> list[str]:
    """Ktoré enginy sa na tomto inštrumente dajú spustiť — podľa toho, čo je na disku.

    Freqtrade potrebuje súbor pre `timeframe` (vyšší TF si z 1m nedopočíta), emulátor
    jediný 1m súbor. Chýbajúce dáta pre Dukascopy doplní `tester.dukas_import`.
    """
    out = []
    if freqtrade_file(inst, timeframe).exists():
        out.append(FREQTRADE)
    if one_minute_file(inst).exists():
        out.append(MULTICHARTS)
    return out


def default_engine(inst: InstrumentSpec, timeframe: str = "3m") -> str:
    """Predvolený engine: Freqtrade, ak preň sú dáta; inak emulátor.

    Pre Dukascopy symboly to prakticky znamená emulátor — ten je pre ne referenciou,
    lebo sedí s tým, čo v MultiCharts naozaj pobeží.
    """
    engines = available(inst, timeframe)
    if _is_off_exchange(inst):
        return MULTICHARTS if MULTICHARTS in engines else FREQTRADE
    return engines[0] if engines else FREQTRADE
