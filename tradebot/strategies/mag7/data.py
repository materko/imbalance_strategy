"""Dáta symbolov sily Mag7 + SPX — feeder stratégie (`StrategySpec.htf_feeder`).

Symboly sily (akcie Mag7, index S&P 500) nie sú na grafe. Pine si ich berie cez
`request.security(sym, "1", …)`; tu ich feeder prečíta z 1m skladu sviečok
(`data/tester/<zdroj>/<trh>/<SYMBOL>-1m.feather`) a pre každý bar grafu povie, čo by Pine na
jeho zavretí videl:

  * **pohyb od otvorenia** v % — zavretie poslednej 1m sviečky symbolu pred koncom baru grafu
    voči open jeho prvej sviečky v NY seanse (Pine `f_fromOpen`); keď prvá sviečka dňa nie je
    presne v čase otvorenia, symbol v ten deň vypadne (Pine `f_today`, `ot == chartOpenT`),
  * **bežný pohyb** — priemer |pohybu po `waitMin` minútach| z posledných `typDays` dní pred
    dnešným (aspoň 3 dni),
  * **VWAP od otvorenia** z 1m sviečok nástroja `vwapData` (Pine `vwapNQ` na výpočtovom TF 1m).

Engine ostáva čistý: dostane hotový `Mag7Snapshot` ako `htf`. Bez súboru na disku je symbol
prázdny (sila sa ráta z ostatných); živá MultiCharts študia tieto dáta nemá.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from tradebot.core.paths import TESTER_DATA
from tradebot.core.types import INSTRUMENTS

__all__ = ["Mag7Feeder", "Mag7Snapshot", "SymbolValue", "data_path"]

NY = ZoneInfo("America/New_York")
MIN_MS = 60_000


@dataclass(frozen=True, slots=True)
class SymbolValue:
    move_pct: float | None   #: pohyb od otvorenia v %, None = symbol dnes nemá dáta
    typ_pct: float | None    #: bežný pohyb v %, None = menej ako 3 dni histórie
    weight: float


@dataclass(frozen=True, slots=True)
class Mag7Snapshot:
    """Čo engine dostane na bare grafu, ktorý začína v NY seanse."""

    values: tuple[SymbolValue, ...]
    vwap: float | None   #: VWAP od otvorenia z 1m dát `vwapData`, None = nedá sa
    vwap_symbol: str     #: kľúč nástroja, z ktorého je VWAP


@dataclass(slots=True)
class _Day:
    first: int            #: index prvej 1m sviečky dňa od otvorenia (0 = presne v čase otvorenia)
    open_px: float
    closes: list[float]   #: zavretie podľa minúty od otvorenia, dopredu vyplnené (NaN pred prvou)
    typ: float | None
    cum_pv: list[float] | None = None
    cum_vol: list[float] | None = None


def data_path(key: str):
    """1m súbor nástroja v sklade sviečok."""
    inst = INSTRUMENTS[key]
    source = inst.source or inst.venue
    return TESTER_DATA / source / inst.market / f"{inst.symbol.replace('/', '_')}-1m.feather"


@lru_cache(maxsize=48)
def _load_days(path_s: str, mtime: float, open_min: int, length: int, ref_min: int, typ_days: int,
               with_vwap: bool) -> dict[date, _Day]:
    """Dni NY seansy jedného symbolu. Výsledok sa drží v pamäti procesu (sweepy, hyperopt)."""
    import numpy as np
    import pandas as pd

    df = pd.read_feather(path_s, columns=["date", "open", "high", "low", "close", "volume"])
    ny = df["date"].dt.tz_convert(NY)
    minute = (ny.dt.hour * 60 + ny.dt.minute).to_numpy() - open_min
    keep = (minute >= 0) & (minute < length)
    df = df.loc[keep]
    idx = minute[keep]
    days_col = ny[keep].dt.date.to_numpy()
    o = df["open"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    hlc3 = ((df["high"] + df["low"] + df["close"]) / 3.0).to_numpy(dtype=float) if with_vwap else None
    vol = df["volume"].to_numpy(dtype=float) if with_vwap else None

    out: dict[date, _Day] = {}
    moves: list[float] = []
    if len(days_col) == 0:
        return out
    # hranice dní (dáta sú zoradené podľa času)
    cuts = np.flatnonzero(days_col[1:] != days_col[:-1]) + 1
    starts = np.concatenate(([0], cuts))
    ends = np.concatenate((cuts, [len(days_col)]))
    for a, b in zip(starts, ends):
        d = days_col[a]
        ii = idx[a:b]
        first = int(ii[0])
        closes = np.full(length, np.nan)
        closes[ii] = c[a:b]
        # dopredu vyplniť (request.security drží poslednú hodnotu)
        mask = np.isnan(closes)
        pos = np.where(~mask, np.arange(length), 0)
        np.maximum.accumulate(pos, out=pos)
        filled = closes[pos]
        filled[: first] = np.nan
        typ = sum(moves) / len(moves) if len(moves) >= 3 else None
        open_px = float(o[a])
        day = _Day(first, open_px, filled.tolist(), typ)
        if with_vwap:
            pv = np.zeros(length)
            vv = np.zeros(length)
            pv[ii] = hlc3[a:b] * vol[a:b]
            vv[ii] = vol[a:b]
            day.cum_pv = np.cumsum(pv).tolist()
            day.cum_vol = np.cumsum(vv).tolist()
        out[d] = day
        # bežný pohyb: prvá sviečka, ktorá sa zavrie `ref_min` minút po prvej (Pine `logged`)
        later = np.flatnonzero(ii >= first + ref_min - 1)
        if len(later) and open_px != 0:
            moves.append(abs((float(c[a + later[0]]) - open_px) / open_px * 100.0))
            if len(moves) > typ_days:
                moves.pop(0)
    return out


class Mag7Feeder:
    """Feeder s rozhraním `feed` / `window_for` — pre emulátor MultiCharts aj Freqtrade."""

    def __init__(self, cfg, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.step_ms = max(1, int(chart_tf_minutes)) * MIN_MS
        self.open_min = int(cfg.open_minutes)
        self.length = int(cfg.session_minutes)
        self._symbols = cfg.symbols
        self._cache: dict[str, dict[date, _Day] | None] = {}
        self._day_open: dict[date, int] = {}

    # rozhranie feedera — informatívny TF stratégia nemá, bary grafu nepotrebuje
    def feed(self, bar) -> None:  # noqa: D401 - zhoda s HTFFeeder
        return None

    def _days(self, key: str, with_vwap: bool = False) -> dict[date, _Day] | None:
        ck = f"{key}|{with_vwap}"
        if ck not in self._cache:
            days = None
            if key and key in INSTRUMENTS:
                p = data_path(key)
                if p.exists():
                    days = _load_days(str(p), p.stat().st_mtime, self.open_min, self.length,
                                      int(self.cfg.waitMin), int(self.cfg.typDays), with_vwap)
            self._cache[ck] = days
        return self._cache[ck]

    def _open_ms(self, d: date) -> int:
        ms = self._day_open.get(d)
        if ms is None:
            t = datetime(d.year, d.month, d.day, tzinfo=NY) + timedelta(minutes=self.open_min)
            ms = self._day_open[d] = int(t.timestamp() * 1000)
        return ms

    def window_for(self, ts_ms: int) -> Mag7Snapshot | None:
        """Hodnoty na zavretí baru grafu, ktorý začína v `ts_ms`; mimo NY seansy None."""
        d = datetime.fromtimestamp(ts_ms / 1000, tz=NY).date()
        open_ms = self._open_ms(d)
        if not 0 <= ts_ms - open_ms < self.length * MIN_MS:
            return None
        k = min(self.length - 1, (ts_ms + self.step_ms - open_ms) // MIN_MS - 1)
        values = []
        for key, w in self._symbols:
            days = self._days(key) if w > 0 else None   # symbol s váhou 0 sa ani nenačíta
            day = days.get(d) if days else None
            mv = None
            if day is not None and day.first == 0 and k >= 0:
                px = day.closes[k]
                if not math.isnan(px) and day.open_px:
                    mv = (px - day.open_px) / day.open_px * 100.0
            values.append(SymbolValue(mv, day.typ if day is not None else None, w))
        vwap = None
        vkey = self.cfg.vwapData
        vdays = self._days(vkey, with_vwap=True) if vkey else None
        vday = vdays.get(d) if vdays else None
        if vday is not None and vday.cum_vol is not None and k >= 0 and vday.cum_vol[k] > 0:
            vwap = vday.cum_pv[k] / vday.cum_vol[k]
        return Mag7Snapshot(tuple(values), vwap, vkey or "")
