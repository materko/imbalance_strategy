"""Engine Mag7 + SPX sila 1.0 — port Pine stratégie „Mag7 + SPX sila od NY open".

Priebeh (na každom uzavretom bare grafu, čas New York):

  1. **deň**: prvý bar grafu v NY seanse (9:30–16:00) — open NY = jeho open, nový deň (jeden obchod),
  2. **sila** z `Mag7Snapshot` (feeder `data.py`): pre symbol s pohybom `mv` a bežným pohybom `typ`
     veľkosť `clamp(mv / (zFull × typ))` a smer `sign(mv)`, vážené váhou symbolu;
     sila = 10 × (wMag × veľkosť + wBreadth × zhoda) / (wMag + wBreadth),
  3. **čiara MAG7** = open NY × (1 + vážený priemerný pohyb / 100), vyhladená EMA `magLen` barov grafu
     (od nuly každý deň), **VWAP** od 9:30 z 1m dát (`vwapData`, inak zo sviečok grafu), **EMA** `emaLen`
     na TF grafu,
  4. **vstup** na zavretí baru, ktorý sa zavrie `waitMin`–`entryEnd` minút po otvorení, raz za deň:
     long pri sile ≥ `thr` a zavretí nad VWAP, EMA a čiarou MAG7 (+ voliteľne nad open NY), short zrkadlovo,
  5. **výstup**: stop v bodoch alebo za open NY (+ `slOpenBuf`), cieľ `rr` × skutočný stop od zavretia
     signálnej sviečky; pri `useEod` zatvorenie v čase `eodH:eodM` (zavretie baru).

Engine je čistý: žiadne I/O, žiadny globálny stav; dáta symbolov dostáva od adaptéra ako `htf`.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import (DrawBg, DrawBox, DrawCommand, DrawKind, DrawLabel, DrawLine, DrawUpdate,
                                   LabelStyle, with_alpha)
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.ma import EMA
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import INSTRUMENTS, Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup, ema_bars

from .config import Mag7Config, SlMode
from .data import Mag7Snapshot
from .drawing import M7_EMA, M7_ENTRY, M7_LINE, M7_MEASURE, M7_OPEN, M7_VWAP, M7_WINDOW

__all__ = ["Mag7Engine", "strength"]

NY = ZoneInfo("America/New_York")
_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_VWAP_COLOR = "#f59e0b"
_MAG_COLOR = "#84cc16"
_EMA_COLOR = "#9333ea"
_OPEN_COLOR = "#a21caf"
_WINDOW_BG = "#eab30814"


def _clamp(x: float) -> float:
    return max(-1.0, min(1.0, x))


def strength(snap: Mag7Snapshot | None, cfg: Mag7Config) -> tuple[float | None, float | None]:
    """(sila −10…+10, vážený priemerný pohyb v %) — Pine `sila`, `avgMove`."""
    if snap is None:
        return None, None
    sw = s_mag = s_br = s_mv = 0.0
    for v in snap.values:
        if v.weight > 0 and v.move_pct is not None:
            sw += v.weight
            s_br += v.weight * (1.0 if v.move_pct > 0 else -1.0 if v.move_pct < 0 else 0.0)
            s_mv += v.weight * v.move_pct
            s_mag += v.weight * (_clamp(v.move_pct / (cfg.zFull * v.typ_pct))
                                 if v.typ_pct is not None and v.typ_pct > 0 else 0.0)
    w_sum = cfg.wMag + cfg.wBreadth
    if sw <= 0 or w_sum <= 0:
        return None, None
    return 10.0 * (cfg.wMag * s_mag / sw + cfg.wBreadth * s_br / sw) / w_sum, s_mv / sw


class Mag7Engine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: Mag7Config, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.ema = EMA(int(cfg.emaLen))
        self.warmup = Warmup(self.chart_tf_minutes).add_seeded(
            f"EMA {cfg.emaLen} @{self.chart_tf_minutes}m", ema_bars(int(cfg.emaLen)), self.chart_tf_minutes,
            self._seed_ema)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=4, atr_len=14)
        vinst = INSTRUMENTS.get(cfg.vwapData) if cfg.vwapData else None
        #: VWAP z 1m dát feedera len vtedy, keď je to ten istý nástroj ako graf
        self._vwap_1m = vinst is not None and vinst.symbol == inst.symbol and (vinst.source or vinst.venue) == (
            inst.source or inst.venue)
        self._in_ny = False
        self._day_t: int | None = None
        self.ny_open: float | None = None
        self._traded = False
        self._measured = False
        self.mag_line: float | None = None
        self.vwap: float | None = None
        self._pv = self._vol = 0.0
        self.sila: float | None = None
        self._prev_pts: dict[str, tuple[int, float]] = {}
        #: boxy TP / SL posledného obchodu: (čas signálu, pozícia už bola otvorená)
        self._box: tuple[int, bool] | None = None

    def _seed_ema(self, bars, partial: Bar | None) -> None:
        for b in bars:
            self.ema.push(b.close)

    # ------------------------------------------------------------------ #

    def _line(self, out: EngineOutput, kind, key: str, end: int, y: float | None, color: str, text: str) -> None:
        """Lomená čiara: úsečka od predošlého bodu k zavretiu tohto baru."""
        if not self.cfg.showLines or y is None:
            self._prev_pts.pop(key, None)
            return
        prev = self._prev_pts.get(key)
        if prev is not None:
            out.drawings.append(DrawLine(kind, prev[0], prev[1], end, y, color, width=2 if kind != M7_EMA else 1,
                                         obj_id=f"m7.{key}.{end}", text=text))
        self._prev_pts[key] = (end, y)

    def _stop(self, long: bool, entry: float) -> float:
        cfg = self.cfg
        st = entry - cfg.slPts if long else entry + cfg.slPts
        if cfg.slMode is SlMode.OPEN and self.ny_open is not None:
            o = self.ny_open - cfg.slOpenBuf if long else self.ny_open + cfg.slOpenBuf
            if (long and o < entry) or (not long and o > entry):
                st = o
        return st

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        ema = self.ema.push(bar.close)
        local = datetime.fromtimestamp(bar.time / 1000, tz=NY)
        start_min = local.hour * 60 + local.minute
        in_ny = 0 <= start_min - cfg.open_minutes < cfg.session_minutes
        end = bar.time + self.step_ms
        close_local = datetime.fromtimestamp(end / 1000, tz=NY)
        close_min = close_local.hour * 60 + close_local.minute
        since_open = close_min - cfg.open_minutes

        new_day = in_ny and not self._in_ny
        self._in_ny = in_ny
        if new_day:
            self._day_t = bar.time
            self._traded = False
            self._measured = False
            self.ny_open = bar.open
            self.mag_line = None
            self._pv = self._vol = 0.0
            self._prev_pts.pop("vwap", None)
            self._prev_pts.pop("mag", None)
            self._prev_pts.pop("open", None)

        snap = htf if isinstance(htf, Mag7Snapshot) else None
        sila, avg_move = strength(snap, cfg) if in_ny else (None, None)
        self.sila = sila

        # VWAP od otvorenia: 1m dáta (Pine výpočtový TF), inak sviečky grafu
        if in_ny:
            self._pv += (bar.high + bar.low + bar.close) / 3.0 * bar.volume
            self._vol += bar.volume
            if self._vwap_1m and snap is not None and snap.vwap is not None:
                self.vwap = snap.vwap
            else:
                self.vwap = self._pv / self._vol if self._vol > 0 else None
        else:
            self.vwap = None

        # čiara MAG7 (Pine `magLine`)
        if not in_ny:
            self.mag_line = None
        elif self.ny_open is not None and avg_move is not None:
            raw = self.ny_open * (1.0 + avg_move / 100.0)
            k = 2.0 / (cfg.magLen + 1)
            self.mag_line = raw if self.mag_line is None else self.mag_line + (raw - self.mag_line) * k

        # ---- kresby ------------------------------------------------------ #
        self._line(out, M7_VWAP, "vwap", end, self.vwap, _VWAP_COLOR, "VWAP od 9:30")
        self._line(out, M7_LINE, "mag", end, self.mag_line, _MAG_COLOR, "MAG7")
        self._line(out, M7_EMA, "ema", end, ema if in_ny else None, _EMA_COLOR, f"EMA {cfg.emaLen}")
        self._line(out, M7_OPEN, "open", end, self.ny_open if in_ny else None, _OPEN_COLOR, "Open NY")
        in_entry = in_ny and cfg.waitMin <= since_open <= max(cfg.entryEnd, cfg.waitMin)
        if in_entry:
            out.drawings.append(DrawBg(M7_WINDOW, bar.time, end, _WINDOW_BG, obj_id=f"m7.w.{bar.time}",
                                       text="Okno vstupu"))
        if in_ny and not self._measured and since_open >= cfg.waitMin:
            self._measured = True
            if sila is not None:
                out.drawings.append(DrawLabel(
                    M7_MEASURE, bar.time, bar.high, f"sila {sila:+.1f}", "#f59e0b", style=LabelStyle.NONE,
                    above=True, obj_id=f"m7.m.{bar.time}"))

        # boxy obchodu rastú doprava, kým obchod beží (Pine `box.set_right`)
        if self._box is not None:
            t0, was_open = self._box
            for kind in ("tp", "sl"):
                out.drawings.append(DrawUpdate(f"m7.{kind}.{t0}", "x2_ms", end))
            if ctx.position_size != 0.0:
                self._box = (t0, True)
            elif was_open or bar.time > t0:
                self._box = None

        # ---- výstup v čase ------------------------------------------------ #
        if ctx.position_size != 0.0:
            if cfg.useEod and close_min >= cfg.eodH * 60 + cfg.eodM:
                out.close_session = True
                for order_id in ctx.open_order_ids:
                    out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx, reason="koniec dňa"))
            return out

        # ---- vstup --------------------------------------------------------- #
        if not in_entry or self._traded or sila is None:
            return out
        c = bar.close
        mt = max(cfg.minMove, self.inst.tick_size)
        long_ok = (cfg.allowL and sila >= cfg.thr
                   and (not cfg.useVwap or (self.vwap is not None and c > self.vwap))
                   and (not cfg.useEma or (ema is not None and c > ema))
                   and (not cfg.useMag or (self.mag_line is not None and c > self.mag_line))
                   and (not cfg.useOpen or (self.ny_open is not None and c - self.ny_open >= mt)))
        short_ok = (cfg.allowS and sila <= -cfg.thr
                    and (not cfg.useVwap or (self.vwap is not None and c < self.vwap))
                    and (not cfg.useEma or (ema is not None and c < ema))
                    and (not cfg.useMag or (self.mag_line is not None and c < self.mag_line))
                    and (not cfg.useOpen or (self.ny_open is not None and self.ny_open - c >= mt)))
        if not (long_ok or short_ok):
            return out
        long = long_ok
        stop = self._stop(long, c)
        sl = abs(c - stop)
        if sl < self.inst.tick_size:
            return out
        take = c + sl * cfg.rr if long else c - sl * cfg.rr
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, sl)
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        plan = TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=self.inst.round_price(c),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl)
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"m7:{idx}", idx, direction=plan.direction, plan=plan,
                                      order_type=OrderType.MARKET,
                                      reason=f"{'LONG' if long else 'SHORT'} sila {sila:+.1f}"))
        self._traded = True
        for kind, level, color in ((DrawKind.TP_BOX, plan.take_profit, _LONG_COLOR),
                                   (DrawKind.SL_BOX, plan.stop_loss, _SHORT_COLOR)):
            out.drawings.append(DrawBox(kind, bar.time, max(plan.entry, level), end, min(plan.entry, level), color,
                                        fill_color=with_alpha(color, 80), obj_id=f"m7.{kind[:2]}.{bar.time}",
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
        self._box = (bar.time, False)
        out.drawings.append(DrawLabel(
            M7_ENTRY, bar.time, bar.low if long else bar.high, f"{'LONG' if long else 'SHORT'} sila {sila:+.1f}",
            "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"m7.e.{bar.time}"))
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
