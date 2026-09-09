"""Dva enginy, ktorými sa dá prehrať tá istá stratégia — a kde má každý dáta.

| engine | čo to je | dáta |
|---|---|---|
| `freqtrade` | Freqtrade backtest v podprocese, fill model Freqtradu | súbor na každý timeframe |
| `multicharts` | emulátor MultiCharts v tomto procese (`MCRunner` + broker podľa MultiCharts) | jeden 1m súbor, vyššie TF sa skladajú v pamäti |

Dáta sú pre oba spoločné — `data/tester/<zdroj>/<trh>/`, delené podľa zdroja a trhu,
nie podľa platformy.

Engine **nie je vlastnosť páru**. Krypto sa dá prehrať aj emulátorom a Dukascopy CFD aj
cez Freqtrade — práve na tom stojí porovnanie oboch ciest
([docs/FREQTRADE.md §G](../docs/FREQTRADE.md)). Obmedzuje to len to, aké dáta sú na disku,
a to hovorí `available()`.

Sviečky sú vždy `data/tester/<zdroj>/<trh>/<PÁR>-<TF>.feather` — zdroj (`binance`, `dukascopy`)
aj trh (`spot`, `futures`) sú adresáre, takže z cesty vidno, čo to je.

Podadresár `futures/` a príponu `-futures` v mene si Freqtrade drží natvrdo
(`IDataHandler._pair_data_filename`), pre spot nepridáva nič. Preto sa mu `--datadir`
podáva rôzne podľa trhu — pri futures o úroveň vyššie, aby si `futures/` doplnil sám,
pri spote priamo na `spot/`. Na disku je tým rozloženie súmerné a `data_dir()` je jediné
miesto, kde tú asymetriu treba vedieť.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from tradebot.core.paths import FREQTRADE_DIR, TESTER_DATA
from tradebot.core.types import InstrumentSpec

__all__ = ["FREQTRADE", "MULTICHARTS", "ENGINES", "ENGINE_TITLES",
           "one_minute_file", "freqtrade_file", "market_dir", "data_dir", "freqtrade_config",
           "freqtrade_exchange", "exchange_timeframes", "freqtrade_blocker",
           "available", "default_engine"]

FREQTRADE = "freqtrade"
MULTICHARTS = "multicharts"
ENGINES = (FREQTRADE, MULTICHARTS)

ENGINE_TITLES = {
    FREQTRADE: "Freqtrade",
    MULTICHARTS: "MultiCharts (emulátor)",
}

#: Zdroje, ktoré nie sú ccxt burza — Freqtrade ich vezme len cez vlastný config
#: a nemá pre ne futures podadresár.
_OFF_EXCHANGE = ("dukascopy",)


def _is_off_exchange(inst: InstrumentSpec) -> bool:
    return inst.data_source in _OFF_EXCHANGE


def market_dir(inst: InstrumentSpec) -> Path:
    """`data/tester/<zdroj>/<trh>/` — kde sviečky tohto inštrumentu naozaj ležia."""
    return TESTER_DATA / inst.data_source / inst.market


def data_dir(inst: InstrumentSpec) -> Path:
    """Čo podať Freqtradu ako `--datadir`.

    Pri futures na burze je to o úroveň vyššie než `market_dir` — `futures/` si Freqtrade
    doplní sám. Pri spote (a pri CFD, ktoré bežia cez spotový config) je to priamo
    `market_dir`, lebo tam nič nedopĺňa.
    """
    if _is_off_exchange(inst) or inst.is_spot:
        return market_dir(inst)
    return TESTER_DATA / inst.data_source


def freqtrade_file(inst: InstrumentSpec, timeframe: str) -> Path:
    """`BTC/USDT:USDT`, `3m` → `data/tester/binance/futures/BTC_USDT_USDT-3m-futures.feather`.

    Príponu `-futures` pridáva Freqtrade len tomu, čo u neho beží ako futures; CFD cez
    spotový config ju nemá. Emulátor číta tie isté súbory, takže konvencia je jedna.
    """
    suffix = "" if (_is_off_exchange(inst) or inst.is_spot) else "-futures"
    return market_dir(inst) / f"{inst.data_stem}-{timeframe}{suffix}.feather"


def one_minute_file(inst: InstrumentSpec) -> Path:
    """1m sviečky pre emulátor — z toho istého stromu ako Freqtrade."""
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


@lru_cache(maxsize=8)
def freqtrade_exchange(config: Path) -> str:
    """Meno burzy z Freqtrade configu — podľa nej sa validuje timeframe."""
    try:
        return str(json.loads(config.read_text(encoding="utf-8"))["exchange"]["name"])
    except (OSError, ValueError, KeyError, TypeError):
        return ""


@lru_cache(maxsize=8)
def exchange_timeframes(name: str) -> frozenset[str]:
    """Timeframy, ktoré burza pozná (z ccxt, bez siete). Prázdne = neobmedzujeme."""
    if not name:
        return frozenset()
    try:
        import ccxt

        return frozenset(getattr(ccxt, name)().timeframes or ())
    except Exception:  # noqa: BLE001  (chýbajúce ccxt ani neznáma burza nesmú zhodiť ponuku)
        return frozenset()


def freqtrade_blocker(inst: InstrumentSpec, timeframe: str) -> str | None:
    """Prečo sa tento timeframe nedá prehrať Freqtradom — alebo `None`, keď sa dá.

    Dve rôzne prekážky: chýbajúci súbor (vyšší TF si Freqtrade z 1m nedopočíta) a
    timeframe, ktorý **burza nepozná**. Ten druhý je dôvod, prečo 2m a 4m ostávajú
    len pre emulátor: Freqtrade beh odmietne už pri validácii configu, hoci sviečky
    na disku sú (`tester.timeframes` ich vyrobí pre graf aj pre emulátor).
    """
    if not freqtrade_file(inst, timeframe).exists():
        return f"chýba súbor pre {timeframe}"
    exchange = freqtrade_exchange(freqtrade_config(inst))
    known = exchange_timeframes(exchange)
    if known and timeframe not in known:
        return f"burza {exchange} timeframe {timeframe} nepozná"
    return None


def available(inst: InstrumentSpec, timeframe: str = "3m") -> list[str]:
    """Ktoré enginy sa na tomto inštrumente a timeframe dajú spustiť.

    Freqtrade potrebuje súbor pre `timeframe` a burzu, ktorá ten timeframe pozná;
    emulátor jediný 1m súbor — vyššie TF si skladá sám, takže mu stačí čokoľvek.
    Chýbajúce dáta pre Dukascopy doplní `tester.dukas_import`.
    """
    out = []
    if freqtrade_blocker(inst, timeframe) is None:
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
