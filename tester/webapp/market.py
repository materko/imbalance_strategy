"""Trhy a páry: inštrument páru, pravidlá trhu (spot bez shortov a páky) a ponuka
párov z dát na disku.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from tradebot.core.paths import TESTER_DATA
from tradebot.core.types import INSTRUMENTS, TradeDirection

from .. import engines


#: Kde ležia sviečky ktorého inštrumentu, rieši `tester.engines` — jedno miesto pre
#: oba enginy. Tu ostáva len prehľadanie burzových adresárov pri stavaní ponuky párov.
BINANCE_FUTURES = TESTER_DATA / "binance" / "futures"


BINANCE_SPOT = TESTER_DATA / "binance" / "spot"


def instrument_for_pair(pair: str) -> str:
    for key, inst in INSTRUMENTS.items():
        if inst.symbol == pair:
            return key
    raise ValueError(f"pre pár {pair!r} nie je definovaný InstrumentSpec (tradebot/core/types.py)")


def check_market_rules(pair: str, params: dict[str, Any]) -> None:
    """Na spote sa nedá shortovať ani páčiť — burza nemá čo požičať.

    Freqtrade by short v spot režime ticho zahodil a páka by sa neuplatnila, takže
    by beh vyzeral ako platný výsledok niečoho, čo sa v skutočnosti nedá obchodovať.
    """
    inst = INSTRUMENTS[instrument_for_pair(pair)]
    if not inst.is_spot:
        return
    direction = params.get("tradeDirection")  # stratégia bez tohto poľa (demo: allowShort) sa nekontroluje
    if direction is not None and direction != TradeDirection.LONG_ONLY.value:
        raise ValueError(
            f"{inst.exchange_symbol} je spotový pár — shorty sa na ňom obchodovať nedajú; "
            f"nastav tradeDirection na „{TradeDirection.LONG_ONLY.value}\" (teraz „{direction}\")"
        )
    leverage = params.get("leverage", 1)
    if leverage is not None and float(leverage) > 1:
        raise ValueError(
            f"{inst.exchange_symbol} je spotový pár — páka na ňom nie je; "
            f"nastav leverage na 1 (teraz {leverage:g})"
        )


def _pair_from_base(base: str) -> str | None:
    """`BTC_USDT_USDT` → `BTC/USDT:USDT` (futures), `BTC_USDT` → `BTC/USDT` (spot)."""
    parts = base.split("_")
    if len(parts) == 3:
        return f"{parts[0]}/{parts[1]}:{parts[2]}"
    if len(parts) == 2:
        return f"{parts[0]}/{parts[1]}"
    return None


_PAIRS_CACHE: dict[str, Any] = {"podpis": None, "pairs": []}


def _data_signature() -> tuple[tuple[str, int, int], ...]:
    """Odtlačok dátových súborov (cesta, mtime, veľkosť) - kým sa nezmení, ponuka párov
    je tá istá. Dáta sa menia len po `data_archive merge` a `timeframes.ensure`, no
    `/api/meta` sa pýta pri každom načítaní stránky a čítanie dátumov z feather
    súborov každého páru trvá sekundu."""
    out = []
    for d in (BINANCE_FUTURES, BINANCE_SPOT):
        try:
            for e in os.scandir(d):
                if e.name.endswith(".feather"):
                    st = e.stat()
                    out.append((e.path, st.st_mtime_ns, st.st_size))
        except OSError:
            continue
    for inst in INSTRUMENTS.values():
        if inst.venue != "multicharts" and inst.data_source != "synthetic":
            continue
        p = engines.one_minute_file(inst)
        try:
            st = p.stat()
            out.append((str(p), st.st_mtime_ns, st.st_size))
        except OSError:
            out.append((str(p), -1, -1))
    return tuple(sorted(out))


def available_pairs() -> list[dict[str, Any]]:
    """Páry, pre ktoré sú stiahnuté dáta (futures aj spot, ľubovoľný TF), a ich dátumový
    rozsah. Výsledok drží cache, kým sa dátové súbory nezmenia."""
    podpis = _data_signature()
    if _PAIRS_CACHE["podpis"] == podpis:
        return [dict(p) for p in _PAIRS_CACHE["pairs"]]
    pairs = _scan_pairs()
    _PAIRS_CACHE.update(podpis=podpis, pairs=pairs)
    return [dict(p) for p in pairs]


def _scan_pairs() -> list[dict[str, Any]]:
    import pandas as pd

    from .chart import available_timeframes

    # pár -> súbor, z ktorého sa čítajú dátumy (3m, ak je; inak prvý dostupný TF)
    files: dict[str, Path] = {}
    for p in sorted(BINANCE_FUTURES.glob("*-*-futures.feather")):
        base, _, tf = p.name[: -len("-futures.feather")].rpartition("-")
        if base not in files or tf == "3m":
            files[base] = p
    for p in sorted(BINANCE_SPOT.glob("*-*.feather")):
        base, _, tf = p.name[: -len(".feather")].rpartition("-")
        if base.count("_") != 1:  # BTC_USDT; funding/mark súbory sú vo futures
            continue
        if base not in files or tf == "3m":
            files[base] = p
    out = []
    for base, p in sorted(files.items()):
        pair = _pair_from_base(base)
        if pair is None:
            continue
        try:
            key = instrument_for_pair(pair)
        except ValueError:
            continue
        inst = INSTRUMENTS[key]
        dates = pd.read_feather(p, columns=["date"])["date"]
        tfs = available_timeframes(pair)
        out.append({
            "pair": pair,
            "instrument": key,
            "source": inst.data_source,
            "engines": engines.available(inst),
            "default_engine": engines.default_engine(inst),
            "exchanges": engines.exchanges_for(inst),
            "exchange": "binance",
            "market": inst.market,
            "kind": engines.market_kind(inst),
            "exchange_symbol": inst.exchange_symbol,
            "from": str(dates.min())[:10],
            "to": str(dates.max())[:10],
            "bars": int(len(dates)),
            "has_1m": "1m" in tfs,
            "has_5m": "5m" in tfs,
            "timeframes": tfs,
        })
    # „burza" MultiCharts a syntetické trhy: len 1m súbory, ostatné TF sa skladajú v pamäti
    for key, inst in INSTRUMENTS.items():
        if inst.venue != "multicharts" and inst.data_source != "synthetic":
            continue
        p = engines.one_minute_file(inst)
        if not p.exists():
            continue
        dates = pd.read_feather(p, columns=["date"])["date"]
        tfs = available_timeframes(inst.symbol)
        out.append({
            "pair": inst.symbol,
            "instrument": key,
            "source": inst.data_source,
            "engines": engines.available(inst),
            "default_engine": engines.default_engine(inst),
            "exchanges": engines.exchanges_for(inst),
            "exchange": "synthetic" if inst.data_source == "synthetic" else "multicharts",
            "market": inst.market,
            "kind": engines.market_kind(inst),
            "exchange_symbol": inst.exchange_symbol,
            "from": str(dates.min())[:10],
            "to": str(dates.max())[:10],
            "bars": int(len(dates)),
            "has_1m": True,
            "has_5m": True,
            "timeframes": tfs,
        })
    return out


def only_1m_on_disk(pair: str) -> bool:
    """Má tento pár na disku len 1m a vyššie TF sa skladajú v pamäti?

    Platí to pre všetko, čo nepochádza z burzy: Dukascopy CFD (emulátor MultiCharts) aj
    syntetické trhy (`tester.synthetic`). Burzové páry majú každý TF stiahnutý, lebo len
    tak sedia s tým, čo burza naozaj hlási.
    """
    try:
        inst = INSTRUMENTS[instrument_for_pair(pair)]
    except ValueError:
        return False
    return inst.venue == "multicharts" or inst.data_source == "synthetic"


def is_multicharts_pair(pair: str) -> bool:
    try:
        return INSTRUMENTS[instrument_for_pair(pair)].venue == "multicharts"
    except ValueError:
        return False
