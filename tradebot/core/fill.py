"""Plnenie príkazov **fill v2** (SMERNICA V2 §3, zadanie U4) — Python aj C# (`TradeBot.Backtest.FillV2`) rovnako.

`v1` je dnešné plnenie emulátora MultiCharts (golden testy proti TradingView, porovnanie). `v2` ho nahrádza tam,
kde smernica hovorí, ako sa naozaj plní (m = 1m sviečka, O/H/L, T = tick):

**Futures** (MNQ, MYM, ES/MES, MGC, 6E, BTC perp):

| udalosť | podmienka v minúte | cena |
|---|---|---|
| long limit vstup P | L ≤ P − pass·T | P |
| short limit vstup P | H ≥ P + pass·T | P |
| long TP | H ≥ TP + pass·T | TP |
| short TP | L ≤ TP − pass·T | TP |
| long SL | L ≤ SL | min(SL, O) − slip·T |
| short SL | H ≥ SL | max(SL, O) + slip·T |
| long stop vstup E | H ≥ E | max(E, O) + slip·T |
| short stop vstup E | L ≤ E | min(E, O) − slip·T |
| market / výstup v čase | open | nákup O + slip·T, predaj O − slip·T |

Náklad `cost_ticks · T · hodnota bodu` na každú stranu (BTC: maker % pri limite a TP, taker % inak).

**CFD** (graf je bid, ask = bid + S; S podľa okna v čase New York — hlavná seansa 9:30–16:00, mimo nej S × off,
otvorenie 9:30–9:40 S × open a sklz navyše, ±5 min okolo správ `calendar_us.json` S × news a sklz navyše):

| udalosť | strana | podmienka | cena |
|---|---|---|---|
| long limit vstup P | nákup | L ≤ P − S | P |
| short limit vstup P | predaj | H ≥ P + pass_sell | P |
| long TP | predaj | H ≥ TP + pass_sell | TP |
| short TP | nákup | L ≤ TP − S | TP |
| long SL | predaj | L ≤ SL | min(SL, O) − slip_sl |
| short SL | nákup | H + S ≥ SL | max(SL, O + S) + slip_sl |
| long stop vstup E | nákup | H + S ≥ E | max(E, O + S) + slip_sl |
| short stop vstup E | predaj | L ≤ E | min(E, O) − slip_sl |
| market nákup / predaj | — | open | O + S + slip_mkt / O − slip_mkt |

Limit, ktorý je pri odoslaní už za trhom (long P ≥ O + S, short P ≤ O v minúte odoslania), sa neplní — MT5 ho
odmietne 10015 (`REJECT`). Swap za každú noc (rollover 21:00 UTC) podľa konfigurácie, predvolene 0 s varovaním.

Obom: SL aj TP v tej istej minúte → SL; lepšia cena (price improvement) sa nepočíta. Výstup v čase (koniec seansy,
koniec dát) sa plní na close baru = open nasledujúcej minúty, so sklzom marketu. Hodnoty sú v `fill_v2.json`
(`tradebot.core.paths.FILL_V2_FILE`), nie v kóde.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence
from zoneinfo import ZoneInfo

__all__ = ["FillModel", "REJECT", "model_for", "load_table", "MODES", "news_events_ms"]

MODES = ("v1", "v2")
#: limit za trhom pri odoslaní (CFD) — vstup sa neplní a zapíše sa ako odmietnutý
REJECT = "reject"
_NY = ZoneInfo("America/New_York")
_RTH = (9 * 60 + 30, 16 * 60)
_OPEN = (9 * 60 + 30, 9 * 60 + 40)
_ROLL_HOUR_UTC = 21


def load_table() -> dict[str, Any]:
    from .paths import FILL_V2_FILE

    return json.loads(FILL_V2_FILE.read_text(encoding="utf-8"))


def news_events_ms() -> tuple[int, ...]:
    """Časy udalostí `tester/calendar_us.json` (všetky typy) v UTC ms — okno ±5 min pre CFD."""
    from .paths import TESTER_DIR

    path = TESTER_DIR / "calendar_us.json"
    if not path.exists():
        return ()
    raw = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for blok in (raw.get("events") or {}).values():
        hh, mm = (blok.get("time_et") or "08:30").split(":")
        for d in blok.get("dates") or ():
            try:
                y, m, dd = (int(x) for x in d.split("-"))
            except ValueError:
                continue
            out.append(int(datetime(y, m, dd, int(hh), int(mm), tzinfo=_NY).timestamp() * 1000))
    return tuple(sorted(out))


@dataclass(frozen=True)
class FillModel:
    """Parametre fill v2 jedného nástroja. `kind` = `futures` alebo `cfd`."""

    kind: str
    instrument: str = ""
    tick: float = 0.0
    cost_ticks: float = 0.0
    slip_ticks: float = 0.0
    pass_ticks: float = 0.0
    cost_pct_maker: float = 0.0
    cost_pct_taker: float = 0.0
    slip_pct: float = 0.0
    spread: float = 0.0
    off_mult: float = 2.0
    pass_sell: float = 0.0
    slip_sl: float = 0.0
    slip_mkt: float = 0.0
    open_mult: float = 2.0
    open_slip: float = 0.0
    news_mult: float = 4.0
    news_slip: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    news_min: int = 5
    news: tuple[int, ...] = field(default=(), repr=False)

    # -- JSON (aj pre C#: `instrument_json(..., fill)`) -----------------------
    def to_dict(self) -> dict[str, Any]:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__ if k != "news"}
        d["news"] = list(self.news)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FillModel":
        known = {k: d[k] for k in cls.__dataclass_fields__ if k in d and k != "news"}
        return cls(**known, news=tuple(int(x) for x in d.get("news") or ()))

    # -- pomocné --------------------------------------------------------------
    @property
    def cfd(self) -> bool:
        return self.kind == "cfd"

    def _slip(self, price: float) -> float:
        return self.slip_ticks * self.tick + self.slip_pct * price

    def _pass(self) -> float:
        return self.pass_ticks * self.tick

    def window(self, ms: int) -> tuple[float, float]:
        """(S, sklz navyše) v minúte `ms` (CFD): správy > otvorenie NY > hlavná seansa > mimo seansy."""
        s = self.spread
        if self.news:
            import bisect

            i = bisect.bisect_left(self.news, ms)
            near = min((abs(ms - self.news[j]) for j in (i - 1, i) if 0 <= j < len(self.news)), default=None)
            if near is not None and near <= self.news_min * 60_000:
                return s * self.news_mult, self.news_slip
        t = datetime.fromtimestamp(ms / 1000, _NY)
        m = t.hour * 60 + t.minute
        if t.weekday() < 5 and _OPEN[0] <= m < _OPEN[1]:
            return s * self.open_mult, self.open_slip
        if t.weekday() < 5 and _RTH[0] <= m < _RTH[1]:
            return s, 0.0
        return s * self.off_mult, 0.0

    # -- vstup ----------------------------------------------------------------
    def entry(self, ms: int, o: float, h: float, l: float, *, is_long: bool, kind: str, price: float,
              first_minute: bool) -> tuple[float, bool] | str | None:
        """(cena, na otvorení?) alebo None (nevyplnené) alebo `REJECT` (CFD limit za trhom pri odoslaní).
        `kind` = market / stop / limit; `first_minute` = prvá minúta po odoslaní."""
        if kind == "market":
            if not first_minute:
                return None
            return self.market(ms, o, buy=is_long), True
        if self.cfd:
            s, extra = self.window(ms)
            if kind == "stop":
                if is_long:
                    if h + s >= price:
                        return max(price, o + s) + self.slip_sl + extra, o + s >= price
                    return None
                if l <= price:
                    return min(price, o) - self.slip_sl - extra, o <= price
                return None
            if first_minute and ((is_long and price >= o + s) or (not is_long and price <= o)):
                return REJECT
            if is_long:
                return (price, False) if l <= price - s else None
            return (price, False) if h >= price + self.pass_sell else None
        if kind == "stop":
            sl = self._slip(price)
            if is_long:
                return (max(price, o) + sl, o >= price) if h >= price else None
            return (min(price, o) - sl, o <= price) if l <= price else None
        p = self._pass()
        if is_long:
            return (price, False) if l <= price - p else None
        return (price, False) if h >= price + p else None

    # -- výstup ---------------------------------------------------------------
    def exit(self, ms: int, o: float, h: float, l: float, *, is_long: bool, stop: float,
             tp: float) -> tuple[float, bool, bool] | None:
        """(cena, je to SL, nerozhodnuteľné) alebo None. SL aj TP v jednej minúte -> SL."""
        if self.cfd:
            s, extra = self.window(ms)
            if is_long:
                hit_sl = l <= stop
                hit_tp = h >= tp + self.pass_sell
                sl_px = min(stop, o) - self.slip_sl - extra
            else:
                hit_sl = h + s >= stop
                hit_tp = l <= tp - s
                sl_px = max(stop, o + s) + self.slip_sl + extra
        else:
            p = self._pass()
            if is_long:
                hit_sl = l <= stop
                hit_tp = h >= tp + p
                sl_px = min(stop, o) - self._slip(stop)
            else:
                hit_sl = h >= stop
                hit_tp = l <= tp - p
                sl_px = max(stop, o) + self._slip(stop)
        if hit_sl:
            return sl_px, True, hit_tp
        if hit_tp:
            return tp, False, False
        return None

    def market(self, ms: int, price: float, *, buy: bool) -> float:
        """Trhový príkaz (aj výstup v čase) na cene `price` (bid pri CFD)."""
        if self.cfd:
            s, extra = self.window(ms)
            return price + s + self.slip_mkt + extra if buy else price - self.slip_mkt - extra
        sl = self._slip(price)
        return price + sl if buy else price - sl

    # -- náklad ---------------------------------------------------------------
    def side_fee(self, price: float, *, maker: bool) -> float:
        """Náklad jednej strany ako podiel nominálu (pre `trade_money`): futures `cost_ticks · T / cena`,
        BTC maker / taker %, CFD provízia / cena (spread je už v cene plnenia)."""
        if price <= 0:
            return 0.0
        if self.cfd:
            return self.commission / price
        if self.cost_pct_maker or self.cost_pct_taker:
            return self.cost_pct_maker if maker else self.cost_pct_taker
        return self.cost_ticks * self.tick / price

    def nights(self, open_ms: int, close_ms: int) -> int:
        """Počet rolloverov (21:00 UTC) medzi otvorením a zatvorením — swap CFD."""
        day = 86_400_000
        roll = _ROLL_HOUR_UTC * 3_600_000
        first = (open_ms - roll) // day + 1
        last = (close_ms - roll) // day
        return max(0, last - first + 1)


def model_for(instrument_key: str, mode: str = "v2", *, news: Sequence[int] | None = None) -> FillModel | None:
    """Fill model nástroja pre `mode` (`v1` = None, dnešné plnenie). Nástroj bez riadku v tabuľke v2 = chyba."""
    if mode in (None, "", "v1"):
        return None
    if mode != "v2":
        raise ValueError(f"fill {mode!r}: {', '.join(MODES)}")
    t = load_table()
    if instrument_key in (t.get("futures") or {}):
        d = dict(t["futures"][instrument_key])
        return FillModel(kind="futures", instrument=instrument_key, **{k: float(v) for k, v in d.items()})
    if instrument_key in (t.get("cfd") or {}):
        d = {k: v for k, v in t["cfd"][instrument_key].items() if k != "as"}
        ev = tuple(news) if news is not None else news_events_ms()
        return FillModel(kind="cfd", instrument=instrument_key, news=ev, **{k: float(v) for k, v in d.items()})
    raise ValueError(f"fill v2: nástroj {instrument_key} nemá v tradebot/core/fill_v2.json parametre (SMERNICA V2 §3)")
