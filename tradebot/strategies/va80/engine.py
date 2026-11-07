"""Engine MTK RANGE 1.0 — pravidlo 80 % (Market Profile) bar po bare.

Čas New York, RTH = bary s otvorením 9:30 ≤ t < 16:00 v pracovný deň. Na každom uzavretom bare:

  1. **nový deň RTH** — z barov predošlého dňa sa spočíta value area (`_value_area`), zapamätá sa otvorenie dňa a či je
     nad VAH / pod VAL aspoň o `minOpenOutside` šírky VA; extrém dňa a stav signálu od nuly,
  2. **profil dňa** — zavretie a objem baru do koša (`vaBinPct` % otvorenia dňa, zaokrúhlené na tick),
  3. **výstup v čase** — pozícia a koniec baru ≥ `exitTime` → zavrieť,
  4. **návrat** — na poslednom bare každej sviečky `returnBarMin` minút od 9:30: nabitie otvorením mimo VA (alebo
     zavretím sviečky mimo VA — bez `requireOpenOutside` a po prvom pokuse), prvé zavretie späť vo VA (do `lastEntry`)
     je pokus, najviac `maxTradesPerDay` za deň: stop za extrémom dňa + `slBufferVa` × šírka VA, cieľ POC / opačný okraj /
     stred; neplatný plán (stop alebo cieľ na zlej strane, RR pod `minRR`) deň ukončí bez obchodu.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawCommand, DrawLine, LineStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext
from tradebot.core.types import Bar, InstrumentSpec
from tradebot.core.warmup import Warmup

from ..rqport import TradeDraw, close_all, market_entry
from .config import Va80Config
from .drawing import VA80_ENTRY, VA80_LEVEL

__all__ = ["Va80Engine", "value_area"]

NY = ZoneInfo("America/New_York")
_OPEN, _CLOSE = 570, 960
_VAH, _VAL, _POC = "#089981", "#f23645", "#5b9cf6"


def value_area(bins: dict[float, float], pct: float, method: str) -> tuple[float, float, float] | None:
    """(VAH, VAL, POC) z objemov košov. POC = kôš s najväčším objemom (pri zhode nižšia cena).

    rank: najobjemnejšie koše (pri zhode nižšia cena), kým súčet nepresiahne `pct` % (POC vždy);
    expand: od POC sa pridáva sused (vyšší / nižší kôš) s väčším objemom, kým súčet nedosiahne `pct` %."""
    if not bins:
        return None
    prices = sorted(bins)
    tot = sum(bins[p] for p in prices)
    if tot <= 0:
        return None
    poc = max(prices, key=lambda p: (bins[p], -p))
    limit = pct / 100.0 * tot
    if method == "expand":
        i = j = prices.index(poc)
        acc = bins[poc]
        while acc < limit and (i > 0 or j < len(prices) - 1):
            up = bins[prices[j + 1]] if j < len(prices) - 1 else -1.0
            dn = bins[prices[i - 1]] if i > 0 else -1.0
            if up >= dn:
                j += 1
                acc += up
            else:
                i -= 1
                acc += dn
        return prices[j], prices[i], poc
    chosen, acc = [], 0.0
    for p in sorted(prices, key=lambda p: (-bins[p], p)):
        acc += bins[p]
        if acc <= limit or p == poc:
            chosen.append(p)
    return max(chosen), min(chosen), poc


class Va80Engine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: Va80Config, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.history = BarHistory(maxlen=2, atr_len=14)
        self.warmup = Warmup(self.chart_tf_minutes).add("profil predošlého dňa a ATR 14 dní", 24 * 1440 // self.chart_tf_minutes)
        self.required_history = self.warmup.chart_bars
        self.day = None
        self.bins: dict[float, float] = {}
        self.bin_step = 0.0
        self.va: tuple[float, float, float] | None = None
        self.side = 0                # nabité: -1 short (cena nad VAH), +1 long (pod VAL), 0 nič
        self.trades = 0
        self.done = False
        self.ext_h = self.ext_l = 0.0
        self.day_start_ms = 0
        # denné ATR z RTH dní (true range voči predošlému zavretiu, priemer 14 hotových dní)
        self.d_h = self.d_l = self.d_c = None
        self.prev_c: float | None = None
        self.trs: deque[float] = deque(maxlen=14)
        self.draw = TradeDraw(self.step_ms)

    def _bin(self, price: float) -> float:
        return self.inst.round_price(round(price / self.bin_step) * self.bin_step)

    @property
    def atr(self) -> float | None:
        return sum(self.trs) / len(self.trs) if len(self.trs) == self.trs.maxlen else None

    def _new_day(self, out: EngineOutput, bar: Bar, day) -> None:
        cfg = self.cfg
        if self.bins:
            self.va = value_area(self.bins, cfg.vaPct, cfg.vaMethod)
        if self.d_h is not None:
            tr = self.d_h - self.d_l if self.prev_c is None else max(self.d_h, self.prev_c) - min(self.d_l, self.prev_c)
            self.trs.append(tr)
            self.prev_c = self.d_c
        self.d_h, self.d_l = bar.high, bar.low
        self.day = day
        self.bins = {}
        tick = self.inst.tick_size
        self.bin_step = max(tick, round(bar.open * cfg.vaBinPct / 100.0 / tick) * tick)
        self.done = False
        self.side = 0
        self.trades = 0
        self.ext_h, self.ext_l = bar.high, bar.low
        self.day_start_ms = bar.time
        if self.va is None:
            return
        vah, val, poc = self.va
        width = vah - val
        if width <= 0:
            return
        if bar.open > vah + cfg.minOpenOutside * width:
            self.side = -1
        elif bar.open < val - cfg.minOpenOutside * width:
            self.side = 1
        if cfg.showLevels:
            end = bar.time + (_CLOSE - _OPEN) * 60_000
            for y, col, n, txt in ((vah, _VAH, "h", "VAH"), (val, _VAL, "l", "VAL"), (poc, _POC, "p", "POC")):
                out.drawings.append(DrawLine(VA80_LEVEL, bar.time, y, end, y, col, style=LineStyle.DASHED,
                                             obj_id=f"va80.{n}.{bar.time}", text=f"{txt} včera"))

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        pos = ctx.position_size
        self.draw.tick(out, bar, pos)
        t = datetime.fromtimestamp(bar.time / 1000, tz=NY)
        m = t.hour * 60 + t.minute
        if t.weekday() >= 5 or not _OPEN <= m < _CLOSE:
            return out
        end_m = m + self.chart_tf_minutes
        end_hm = end_m // 60 * 100 + end_m % 60

        # ---- 1. nový deň ------------------------------------------------------ #
        if t.date() != self.day:
            self._new_day(out, bar, t.date())
        # ---- 2. profil a extrém dňa ------------------------------------------- #
        b = self._bin(bar.close)
        self.bins[b] = self.bins.get(b, 0.0) + float(bar.volume)
        self.ext_h, self.ext_l = max(self.ext_h, bar.high), min(self.ext_l, bar.low)
        self.d_h, self.d_l, self.d_c = max(self.d_h, bar.high), min(self.d_l, bar.low), bar.close

        # ---- 3. výstup v čase -------------------------------------------------- #
        if pos != 0.0 and end_hm >= int(cfg.exitTime):
            close_all(out, ctx, idx, f"výstup v čase {int(cfg.exitTime):04d}")
            return out

        # ---- 4. návrat do VA na zavretí sviečky returnBarMin ---------------------- #
        # nabitie: otvorenie mimo VA (pri novom dni) alebo zavretie sviečky mimo VA (bez `requireOpenOutside`, alebo po
        # prvom pokuse dňa); vybitie: zavretie sviečky späť vo VA = pokus, najviac `maxTradesPerDay` za deň
        if self.done or self.va is None or pos != 0.0 or (end_m - _OPEN) % int(cfg.returnBarMin) != 0:
            return out
        if end_hm > int(cfg.lastEntry):
            self.done = True
            return out
        vah, val, poc = self.va
        if not val <= bar.close <= vah:
            if not cfg.requireOpenOutside or self.trades > 0:
                self.side = -1 if bar.close > vah else 1
            return out
        if self.side == 0 or self.trades >= int(cfg.maxTradesPerDay):
            return out
        self.trades += 1
        long = self.side > 0
        self.side = 0
        stop_h, stop_l = self.ext_h, self.ext_l
        self.ext_h, self.ext_l = bar.high, bar.low          # extrém ďalšieho výbehu sa počíta od tohto pokusu
        if (long and not cfg.allowLong) or (not long and not cfg.allowShort):
            return out
        width = vah - val
        stop = stop_l - cfg.slBufferVa * width if long else stop_h + cfg.slBufferVa * width
        take = {"poc": poc, "opp": vah if long else val, "mid": (vah + val) / 2}[cfg.tpMode]
        entry = bar.close
        if cfg.minRR > 0 and abs(take - entry) < cfg.minRR * abs(entry - stop):
            return out
        if cfg.maxStopAtr > 0 and (self.atr is None or abs(entry - stop) > cfg.maxStopAtr * self.atr):
            return out
        plan = market_entry(out, cfg, self.inst, bar, idx, "va80", long, stop, take,
                            f"návrat do včerajšej VA ({'long' if long else 'short'})")
        if plan:
            self.draw.start(out, bar, "va80", plan.entry, plan.stop_loss, plan.take_profit, VA80_ENTRY,
                            "VA long" if long else "VA short", long)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
