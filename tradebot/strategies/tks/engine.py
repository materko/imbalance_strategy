"""Engine TKS 1.0 — NQ Kompas (presne ako Pine `nq_kompas.pine`) a vstup po `nConf` sviečkach za hranicou.

Kompas sa počíta na baroch grafu len v seanse NY 9:30–16:00 (minúta = čas **zavretia** baru od 9:30):

  * únik zo šumu: (close / open dňa − 1) / σ, σ = priemer |close / open − 1| v tej istej minúte za `lookbackDays`
    predošlých dní (aspoň polovica) → tanh(x / 2),
  * noc: poloha close v nočnom range (prvý bar po 18:00 až 9:30) → (pos − 0,5) × 2, orezané ±1,5, / 1,5,
  * tlak: Σ (poloha zavretia v sviečke × objem) / Σ objem od 9:30, / `PRESS_SCALE`, orezané ±1,
  * VWAP: podiel barov od 9:30 so zavretím nad VWAP (od 9:30) → 2 × podiel − 1,
  * Kompas = 50 + 50 × priemer štyroch.

Signál: `nConf` barov po sebe s Kompasom pod `loLevel` (short) / nad `hiLevel` (long); spotrebuje sa (aj keď sa
nevstúpi) a znova je k dispozícii, až keď Kompas odíde od hranice. Vstup market na zavretí (plní sa na otvorení ďalšieho
baru), SL = najbližší potvrdený swing high nad close (short) / swing low pod close (long) — alebo ATR / pevné body
(`slMode`), so stropom vzdialenosti (`maxSlPoints`, `maxSlAtr`) —, TP = close ± RR × |close − SL|. Vstupy len v časovom
okne `entryStartMin`–`entryEndMin` mimo prestávky `pauseFromMin`–`pauseToMin` (minúty po 9:30); filtre signál spotrebujú.
"""

from __future__ import annotations

import math
from collections import deque

from tradebot.core.drawing import DrawCommand
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext
from tradebot.core.types import Bar, InstrumentSpec
from tradebot.core.warmup import Warmup

from ._common import TradeHelper, ny
from .config import PRESS_SCALE, SlMode, TksConfig
from .drawing import TKS_ENTRY

__all__ = ["TksEngine", "Kompas"]

_OPEN, _CLOSE = 570, 960            # 9:30, 16:00 New York
_SLOTS = 391


class Kompas:
    """NQ Kompas bar po bare. ``push(bar)`` vráti hodnotu 0–100 alebo ``None`` (mimo seansy / málo histórie)."""

    def __init__(self, tf_minutes: int, lookback: int = 14) -> None:
        self.tf = max(1, int(tf_minutes))
        self.lookback = int(lookback)
        self.hist: deque[list[float | None]] = deque(maxlen=self.lookback)
        self.today: list[float | None] = [None] * _SLOTS
        self.day = None
        self.open: float | None = None
        self.on_hi = self.on_lo = None          # bežiaci nočný range
        self.day_on_hi = self.day_on_lo = None  # nočný range pred dnešnou seansou
        self.prev_on = False
        self.cpv = self.cv = self.pn = 0.0
        self.nb = self.na = 0
        self.rth = False
        self.k_close = 0

    def push(self, bar: Bar) -> float | None:
        t = ny(bar.time)
        m = t.hour * 60 + t.minute                      # minúta OTVORENIA baru
        wd = t.weekday()
        rth = _OPEN <= m < _CLOSE and wd < 5
        onseg = (m >= 1080 or m < _OPEN) and not rth
        self.rth = rth
        if onseg and not self.prev_on:
            self.on_hi, self.on_lo = bar.high, bar.low
        elif onseg:
            self.on_hi, self.on_lo = max(self.on_hi, bar.high), min(self.on_lo, bar.low)
        self.prev_on = onseg
        if not rth:
            return None
        day = (t.year, t.month, t.day)
        if day != self.day:
            if self.day is not None and self.open is not None:
                self.hist.append(self.today)
            self.today = [None] * _SLOTS
            self.day, self.open = day, bar.open
            self.day_on_hi, self.day_on_lo = self.on_hi, self.on_lo
            self.cpv = self.cv = self.pn = 0.0
            self.nb = self.na = 0
        k = m + self.tf - _OPEN
        self.k_close = k
        if not 1 <= k < _SLOTS:
            return None
        c = bar.close
        self.today[k] = abs(c / self.open - 1)
        self.cpv += (bar.high + bar.low + c) / 3 * bar.volume
        self.cv += bar.volume
        rng = bar.high - bar.low
        clv = ((c - bar.low) - (bar.high - c)) / rng if rng > 0 else 0.0
        self.pn += clv * bar.volume
        vw = self.cpv / self.cv if self.cv > 0 else c
        self.nb += 1
        self.na += c > vw
        vals = [d[k] for d in self.hist if d[k] is not None]
        if len(vals) < max(3, self.lookback // 2) or sum(vals) <= 0:
            return None
        sig = sum(vals) / len(vals)
        ne = (c / self.open - 1) / sig
        hi, lo = self.day_on_hi, self.day_on_lo
        onpos = (c - lo) / (hi - lo) if hi is not None and lo is not None and hi > lo else 0.5
        c1 = math.tanh(ne / 2.0)
        c2 = max(-1.5, min(1.5, (onpos - 0.5) * 2.0)) / 1.5
        c3 = max(-1.0, min(1.0, (self.pn / self.cv if self.cv > 0 else 0.0) / PRESS_SCALE))
        c4 = 2.0 * self.na / self.nb - 1.0
        return 50 + 50 * (c1 + c2 + c3 + c4) / 4


class TksEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: TksConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg, self.inst = cfg, inst
        self.tf = max(1, int(chart_tf_minutes))
        self.step_ms = self.tf * 60_000
        self.kompas = Kompas(self.tf, int(cfg.lookbackDays))
        self.value: float | None = None
        piv = int(cfg.pivLen)
        self.history = BarHistory(maxlen=2 * piv + 4, atr_len=int(cfg.atrLen))
        self.swing_hi: deque[float] = deque(maxlen=200)
        self.swing_lo: deque[float] = deque(maxlen=200)
        self.cnt_dn = self.cnt_up = 0
        self.armed_dn = self.armed_up = True
        self.sess_day = None
        self.sess_trades = 0
        self.helper = TradeHelper(inst, self.step_ms, "tks", TKS_ENTRY)
        days = int(cfg.lookbackDays) + 2
        self.warmup = Warmup(self.tf).add(f"NQ Kompas {cfg.lookbackDays} dní", days * 1440 // self.tf)
        self.required_history = self.warmup.chart_bars

    def _pivots(self) -> None:
        """Swing potvrdený `pivLen` barmi na každej strane (ako Python test; v Pine ta.pivothigh / pivotlow)."""
        p = int(self.cfg.pivLen)
        h = self.history
        if not h.has(2 * p):
            return
        mid = h[p]
        win = [h[i] for i in range(2 * p + 1)]
        if mid.high == max(b.high for b in win):
            self.swing_hi.append(mid.high)
        if mid.low == min(b.low for b in win):
            self.swing_lo.append(mid.low)

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        cfg, out = self.cfg, EngineOutput()
        self.history.append(bar)
        idx = self.history.bar_index
        self.helper.track(out, bar, ctx)
        self._pivots()
        k = self.kompas.push(bar)
        self.value = k
        pos = ctx.position_size
        if self.kompas.rth and self.kompas.day != self.sess_day:
            self.sess_day, self.sess_trades = self.kompas.day, 0
        if cfg.closeAtSessionEnd and pos != 0.0 and self.kompas.rth and self.kompas.k_close >= 390:
            self.helper.close(out, ctx, idx, "koniec seansy 16:00")
            return out
        if k is None:
            self.cnt_dn = self.cnt_up = 0
            self.armed_dn = self.armed_up = True
            return out
        self.cnt_dn = self.cnt_dn + 1 if k < cfg.loLevel else 0
        self.cnt_up = self.cnt_up + 1 if k > cfg.hiLevel else 0
        if k >= cfg.loLevel:
            self.armed_dn = True
        if k <= cfg.hiLevel:
            self.armed_up = True
        side = 0
        if self.cnt_dn >= int(cfg.nConf) and self.armed_dn:
            self.armed_dn = False
            side = -1
        elif self.cnt_up >= int(cfg.nConf) and self.armed_up:
            self.armed_up = False
            side = 1
        if side == 0 or pos != 0.0:
            return out
        if int(cfg.maxTradesPerSession) and self.sess_trades >= int(cfg.maxTradesPerSession):
            return out
        if (side < 0 and not cfg.allow_short) or (side > 0 and not cfg.allow_long):
            return out
        kc = self.kompas.k_close                       # minúta zavretia od 9:30
        if not (int(cfg.entryStartMin) <= kc <= int(cfg.entryEndMin)):
            return out
        if int(cfg.pauseFromMin) < int(cfg.pauseToMin) and int(cfg.pauseFromMin) <= kc < int(cfg.pauseToMin):
            return out
        c = bar.close
        atr = self.history.atr
        if cfg.slMode is SlMode.SWING:
            if side < 0:
                sl = next((x for x in reversed(self.swing_hi) if x > c), None)
            else:
                sl = next((x for x in reversed(self.swing_lo) if x < c), None)
        else:
            d0 = float(cfg.slAtrMult) * atr if cfg.slMode is SlMode.ATR else float(cfg.slPoints)
            sl = c - side * d0 if d0 > 0 else None
        if sl is None:
            return out
        dist = abs(c - sl)
        if (float(cfg.maxSlPoints) > 0 and dist > float(cfg.maxSlPoints)) or \
                (float(cfg.maxSlAtr) > 0 and atr > 0 and dist > float(cfg.maxSlAtr) * atr):
            return out
        take = c + side * float(cfg.rrRatio) * dist
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, dist)
        plan = self.helper.plan(side > 0, c, sl, take, qty if qty > 0 else 1.0)
        if plan is None:
            return out
        self.helper.enter(out, bar, idx, plan, f"Kompas {k:.0f} — {int(cfg.nConf)} sviečky za hranicou",
                          f"{'LONG' if side > 0 else 'SHORT'} Kompas {k:.0f}")
        self.sess_trades += 1
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
