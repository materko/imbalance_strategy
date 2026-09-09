"""Dáta pre graf páru v detaile behu: sviečky z feather súborov a orezanie kresieb.

Sviečky sa **neukladajú k behu** — sú v `data/` platformy (a v archíve v gite), takže
by sa len duplikovali. K behu patria iba kresby enginu (`chart.json.gz`), lebo tie
závisia od parametrov a znovu ich vyrobiť znamená prehrať celý backtest.

Prehliadač nikdy nedostane celý rok: sviečky sa čítajú po oknách (max
`MAX_CANDLES` na požiadavku) a kresby sa orezú na objekty, ktoré do okna zasahujú.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from tradebot.core.candles import resample_ohlcv
from tradebot.core.types import INSTRUMENTS
from .. import engines
from .. import timeframes as tf_config
from .runner import instrument_for_pair, is_multicharts_pair

#: Timeframy, ktoré má zmysel ponúknuť v grafe — zdrojový 1m plus tie z `timeframes.json`,
#: zoradené od najkratšieho. Pri burzových pároch musí súbor existovať (graf nič neskladá);
#: doplní ich `tester.timeframes` pri štarte webapp.
TIMEFRAMES = tuple(sorted({tf_config.SOURCE_TF, *tf_config.wanted()}, key=tf_config.minutes))

#: Horná hranica sviečok v jednej odpovedi. Plotly kreslí ~6 000 sviečok bez trhania;
#: pri väčšom okne si má stránka vypýtať hrubší timeframe.
MAX_CANDLES = 6000


def pair_file(pair: str, timeframe: str) -> Path:
    """`BTC/USDT:USDT`, `3m` → `.../futures/BTC_USDT_USDT-3m-futures.feather`,
    spotový `BTC/USDT` → `.../BTC_USDT-3m.feather` (Freqtrade pomenovanie)."""
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"nepodporovaný timeframe {timeframe!r}; povolené: {', '.join(TIMEFRAMES)}")
    inst = INSTRUMENTS[instrument_for_pair(pair)]
    if is_multicharts_pair(pair):
        # Dukascopy má na disku len 1m; ostatné TF sa skladajú v pamäti (`core.candles`)
        return engines.one_minute_file(inst)
    return engines.freqtrade_file(inst, timeframe)


def available_timeframes(pair: str) -> list[str]:
    """Timeframy, pre ktoré má pár dáta. Neznámy pár nemá žiadne — nie je to chyba, len
    prázdna ponuka (validáciu behu rieši `app.submit`, ktorá povie, čo je zle)."""
    try:
        inst = INSTRUMENTS[instrument_for_pair(pair)]
    except ValueError:
        return []
    if is_multicharts_pair(pair):
        # Dukascopy má na disku len 1m, vyššie TF sa skladajú v pamäti
        return list(TIMEFRAMES) if engines.one_minute_file(inst).exists() else []
    return [tf for tf in TIMEFRAMES if engines.freqtrade_file(inst, tf).exists()]


@lru_cache(maxsize=6)
def _frame(path: str, mtime_ns: int, minutes: int = 1):
    """Sviečky ako numpy polia; cache podľa cesty a mtime (súbor sa mení len po merge dát).
    `minutes` > 1 poskladá TF z 1m v pamäti („burza" MultiCharts má na disku len 1m)."""
    import pandas as pd

    df = pd.read_feather(path, columns=["date", "open", "high", "low", "close", "volume"])
    df = resample_ohlcv(df, minutes)
    ts = (df["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000).to_numpy()
    cols = {c: df[c].astype(float).to_numpy() for c in ("open", "high", "low", "close", "volume")}
    return ts, cols


def candles(pair: str, timeframe: str, from_ms: int, to_ms: int, limit: int = MAX_CANDLES) -> dict[str, Any]:
    """Sviečky v okne `[from_ms, to_ms)`, najviac `limit` — vtedy sa okno oreže odpredu
    a `truncated` je `True`, aby si stránka mohla vybrať hrubší timeframe."""
    import numpy as np

    path = pair_file(pair, timeframe)
    if not path.exists():
        raise FileNotFoundError(f"chýbajú {timeframe} dáta pre {pair} ({path.name})")
    minutes = _tf_minutes(timeframe) if is_multicharts_pair(pair) else 1
    ts, cols = _frame(str(path), path.stat().st_mtime_ns, minutes)
    a = int(np.searchsorted(ts, from_ms, side="left"))
    b = int(np.searchsorted(ts, to_ms, side="left"))
    truncated = b - a > limit
    if truncated:
        b = a + limit
    sl = slice(a, b)
    return {
        "pair": pair,
        "timeframe": timeframe,
        "from_ms": int(ts[a]) if b > a else from_ms,
        "to_ms": int(ts[b - 1]) if b > a else to_ms,
        "truncated": truncated,
        "t": ts[sl].tolist(),
        "o": cols["open"][sl].tolist(),
        "h": cols["high"][sl].tolist(),
        "l": cols["low"][sl].tolist(),
        "c": cols["close"][sl].tolist(),
        "v": cols["volume"][sl].tolist(),
    }


def _tf_minutes(tf: str) -> int:
    n, unit = int(tf[:-1]), tf[-1]
    return n * {"m": 1, "h": 60, "d": 1440}[unit]


def window(chart: dict[str, Any], from_ms: int, to_ms: int) -> list[dict[str, Any]]:
    """Objekty, ktoré zasahujú do okna. Box s `extend.right` siaha až po koniec okna."""
    out = []
    for d in chart.get("objects", []):
        if d["t"] == "label":
            x1 = x2 = d["x"]
        else:
            x1, x2 = d["x1"], d["x2"]
            if d.get("er"):
                x2 = max(x2, to_ms)
        if x2 >= from_ms and x1 <= to_ms:
            out.append(d)
    return out


def summary(chart: dict[str, Any]) -> dict[str, Any]:
    """Hlavička bez objektov — pár, timeframe, rozsah, počty podľa druhu."""
    return {k: v for k, v in chart.items() if k != "objects"}
