"""Engine FPC 1.0 — férová cena (Fair Pricing Theory podľa JJ Simona).

Priebeh (na každom uzavretom bare grafu, čas New York podľa otvorenia baru):

  1. **správa**: na bare v čase správy (8:30) sa zapamätá jeho open = cena pred správou; správa je
     „skok", keď je rozsah baru aspoň `newsMult` × priemerný rozsah `newsAvgBars` barov pred ním,
  2. **okno**: NY ráno / poobede / Ázia / Londýn (`useS{k}`, `s{k}H`, `s{k}M`, `s{k}Len`), v deň správy
     aj okno „po správe" (od baru za správou do začiatku NY ráno); na prvom bare okna sa určí
     **férová cena** (open baru; NY ráno v deň správy cena pred správou; poobede voliteľne ranná),
     smer prvej sviečky, jej rozsah a **bias** (opak pohybu za posledných `biasH` hodín),
  3. **signály**: displacement (telo väčšie ako predošlé, predošlá opačnej farby, zavretie za jej knôt)
     a prieraz štruktúry (zavretie za posledný swing knôt, `pivLen` barov z každej strany),
  4. **pokračovanie** (raz za okno, prvých `contWin` minút): signál v smere prvej sviečky, voliteľne len
     v súlade s biasom; TP / SL `contTP` / `contSL`, pri otváracej sviečke nad `bigBar` × 2,
  5. **návrat**: nad férovou cenou short, pod ňou long, keď je k nej aspoň `minPct` % z TP (pevný cieľ)
     alebo `minDist` (cieľ na férovej cene); filtre: trendový deň (VWAP okna), max. vzdialenosť,
     pauza po strate, oneskorenie návratov, pevná štruktúra, smer biasu,
  6. **riadenie**: jedna pozícia naraz, najviac `maxTrades` obchodov a `maxLossRow` strát po sebe v okne,
     otvorený obchod sa zavrie `closeAfter` minút po konci okna.

Výsledok obchodu (zisk / strata) si engine odvodí sám z baru, na ktorom pozícia skončila — adaptér mu
povie len veľkosť pozície. Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import (DrawBg, DrawBox, DrawCommand, DrawKind, DrawLabel, DrawLine, DrawUpdate, LabelStyle,
                                   LineStyle, with_alpha)
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .config import WINDOWS, FpcConfig, NewsMode, PmFair, TpMode
from .drawing import FPC_ENTRY, FPC_FAIR, FPC_NEWS, FPC_SIGNAL, FPC_VWAP, FPC_WINDOW, FPC_ZONE

__all__ = ["FpcEngine", "NEWS_WINDOW"]

NY = ZoneInfo("America/New_York")
NEWS_WINDOW = 5   #: číslo okna „po správe"
_NAMES = {**dict(WINDOWS), NEWS_WINDOW: "Po správe"}
_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_FAIR_COLOR = "#f59e0b"
_VWAP_COLOR = "#06b6d4"
_WINDOW_BG = "#3b82f610"
_VWAP_EVERY = 5   #: VWAP okna sa kreslí ako lomená čiara s bodom každých toľko barov


@dataclass(slots=True)
class _Trade:
    """Poslaný obchod — kvôli počítaniu strát po sebe a pauze po strate."""

    long: bool
    entry: float
    stop: float
    take: float
    sent_idx: int
    signal_t: int
    in_pos: bool = False


class FpcEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: FpcConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self._bias_bars = max(1, round(cfg.biasH * 60 / self.chart_tf_minutes))
        n = int(cfg.pivLen)
        self.warmup = (Warmup(self.chart_tf_minutes)
                       .add(f"bias {cfg.biasH} h", self._bias_bars + 1)
                       .add(f"priemerný rozsah {cfg.newsAvgBars} barov (správa)", int(cfg.newsAvgBars) + 1)
                       .add(f"swing {n}", 2 * n + 2))
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=max(self._bias_bars, int(cfg.newsAvgBars), 2 * n + 1) + 4, atr_len=14)
        # správa
        self._pre_news: float | None = None
        self._news_day: tuple[int, int, int] | None = None
        self._news_active_day: tuple[int, int, int] | None = None
        # okno
        self._sid = 0
        self._sess_t: int | None = None
        self._end_t: int | None = None
        self.fair: float | None = None
        self._fair_src = ""
        self._fair_am: float | None = None
        self._open_dir = 0
        self._open_rng = 0.0
        self.bias = 0
        self._cont_done = True
        self.loss_row = 0
        self._n_trades = 0
        self._w_pv = 0.0
        self._w_vol = 0.0
        self.vwap: float | None = None
        self._vwap_pt: tuple[int, float] | None = None
        # štruktúra
        self._sw_l: float | None = None
        self._sw_h: float | None = None
        self._sw_l_tests = 0
        self._sw_h_tests = 0
        # obchod
        self._trade: _Trade | None = None
        self._last_loss_t: int | None = None

    # ------------------------------------------------------------------ #

    def _window_id(self, minute: int, news_today: bool) -> int:
        cfg = self.cfg
        for k, _ in WINDOWS:
            on, start, length = cfg.window(k)
            if on and (minute - start) % 1440 < length:
                return k
        if news_today and cfg.useNewsWin and cfg.useS1:
            _, start, _ = cfg.window(1)
            if cfg.news_minutes < minute < start:
                return NEWS_WINDOW
        return 0

    def _news(self, bar: Bar, minute: int, day: tuple[int, int, int]) -> bool:
        """Spracuje bar správy; vráti, či je dnes deň správy s platnou cenou pred ňou."""
        cfg = self.cfg
        if cfg.newsMode is NewsMode.OFF:
            return False
        if minute == cfg.news_minutes and self._news_day != day:
            self._news_day = day
            self._pre_news = bar.open
            avg = self.history.sma_range(int(cfg.newsAvgBars))   # bar správy ešte nie je v histórii
            spike = avg > 0 and (bar.high - bar.low) >= cfg.newsMult * avg
            if cfg.newsMode is NewsMode.ALWAYS or spike:
                self._news_active_day = day
        return self._news_active_day == day and self._pre_news is not None

    def _structure(self, bar: Bar) -> tuple[bool, bool]:
        """(prieraz dole, prieraz hore) na tomto bare; potom testy úrovní a nové swingy."""
        cfg = self.cfg
        dn_all = self._sw_l is not None and bar.close < self._sw_l
        up_all = self._sw_h is not None and bar.close > self._sw_h
        dn = dn_all and (not cfg.useTests or self._sw_l_tests >= cfg.minTests)
        up = up_all and (not cfg.useTests or self._sw_h_tests >= cfg.minTests)
        if dn_all:
            self._sw_l = None   # prerazený knôt už neplatí, čaká sa na nový
        if up_all:
            self._sw_h = None
        tol = cfg.testTol.resolve(self.inst, price=bar.close)
        if self._sw_l is not None and bar.low <= self._sw_l + tol:
            self._sw_l_tests += 1
        if self._sw_h is not None and bar.high >= self._sw_h - tol:
            self._sw_h_tests += 1
        n = int(cfg.pivLen)
        if self.history.has(2 * n):
            c = self.history[n]
            side = [self.history[i] for i in range(2 * n + 1) if i != n]
            if all(c.low < x.low for x in side):
                self._sw_l, self._sw_l_tests = c.low, 0
            if all(c.high > x.high for x in side):
                self._sw_h, self._sw_h_tests = c.high, 0
        return dn, up

    def _displacement(self, bar: Bar) -> tuple[bool, bool]:
        if not self.history.has(1):
            return False, False
        p = self.history[1]
        body, pbody = abs(bar.close - bar.open), abs(p.close - p.open)
        dn = bar.close < bar.open and p.close > p.open and body > pbody and bar.close < p.low
        up = bar.close > bar.open and p.close < p.open and body > pbody and bar.close > p.high
        return dn, up

    def _track(self, out: EngineOutput, bar: Bar, ctx: MarketContext, idx: int) -> None:
        """Výsledok posledného obchodu: strata = stop na bare konca, alebo (bez stopu aj cieľa) zavretie
        horšie ako vstup — pre straty po sebe a pauzu po strate."""
        tr = self._trade
        if tr is None:
            return
        for kind in ("tp", "sl"):   # boxy obchodu rastú doprava, kým obchod beží
            out.drawings.append(DrawUpdate(f"fpc.{kind}.{tr.signal_t}", "x2_ms", bar.time + self.step_ms))
        if ctx.position_size != 0.0:
            tr.in_pos = True
            return
        if not tr.in_pos and idx <= tr.sent_idx:
            return   # bar, na ktorom sa order poslal
        hit_sl = bar.low <= tr.stop if tr.long else bar.high >= tr.stop
        hit_tp = bar.high >= tr.take if tr.long else bar.low <= tr.take
        loss = hit_sl or (not hit_tp and ((bar.close < tr.entry) if tr.long else (bar.close > tr.entry)))
        if loss:
            self.loss_row += 1
            self._last_loss_t = bar.time
        else:
            self.loss_row = 0
        self._trade = None

    def _plan(self, long: bool, entry: float, tp: float, sl: float) -> TradePlan | None:
        if sl < self.inst.tick_size * 2 or tp <= 0:
            return None
        cfg = self.cfg
        stop = entry - sl if long else entry + sl
        take = entry + tp if long else entry - tp
        qty = self.inst.qty_for_risk(cfg.riskDollar, sl) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl)

    # ------------------------------------------------------------------ #

    def _start_window(self, out: EngineOutput, bar: Bar, sid: int, news_today: bool) -> None:
        cfg = self.cfg
        self._sess_t = bar.time
        self._open_dir = 1 if bar.close > bar.open else -1 if bar.close < bar.open else 0
        self._open_rng = bar.high - bar.low
        ref = self.history[self._bias_bars].close if self.history.has(self._bias_bars) else None
        self.bias = 0 if ref is None else (1 if bar.open < ref else -1 if bar.open > ref else 0)
        self._cont_done = sid == NEWS_WINDOW
        self.loss_row = 0
        self._n_trades = 0
        self._w_pv = self._w_vol = 0.0
        self.vwap = None
        self._vwap_pt = None
        if sid == NEWS_WINDOW or (sid == 1 and news_today):
            self.fair, self._fair_src = self._pre_news, f"pred správou {cfg.newsH}:{cfg.newsM:02d}"
        elif sid == 2 and cfg.pmFair is PmFair.MORNING and self._fair_am is not None:
            self.fair, self._fair_src = self._fair_am, "z rána"
        else:
            self.fair, self._fair_src = bar.open, f"open {_NAMES[sid]}"
        if sid == 1:
            self._fair_am = self.fair
        end = bar.time + self.step_ms
        out.drawings.append(DrawBg(FPC_WINDOW, bar.time, end, _WINDOW_BG, obj_id=f"fpc.w.{bar.time}",
                                   text=_NAMES[sid]))
        if cfg.showFair:
            out.drawings.append(DrawLine(FPC_FAIR, bar.time, self.fair, end, self.fair, _FAIR_COLOR, width=2,
                                         obj_id=f"fpc.f.{bar.time}", text=f"Férová cena ({self._fair_src})"))
            out.drawings.append(DrawLabel(FPC_FAIR, bar.time, self.fair,
                                          f"Férová cena {self.fair:g} — {self._fair_src}", _FAIR_COLOR,
                                          style=LabelStyle.LEFT, obj_id=f"fpc.fl.{bar.time}"))
        if cfg.showZone:
            z = self._zone_dist(bar.close)
            for sign, tag in ((1, "p"), (-1, "m")):
                y = self.fair + sign * z
                out.drawings.append(DrawLine(FPC_ZONE, bar.time, y, end, y, _FAIR_COLOR, style=LineStyle.DOTTED,
                                             obj_id=f"fpc.z{tag}.{bar.time}", text="Pásmo bez vstupu"))

    def _extend_window(self, out: EngineOutput, bar: Bar) -> None:
        """Okno, férová cena a pásmo pokračujú po koniec tohto baru."""
        cfg = self.cfg
        t0, end = self._sess_t, bar.time + self.step_ms
        out.drawings.append(DrawUpdate(f"fpc.w.{t0}", "x2_ms", end))
        if cfg.showFair:
            out.drawings.append(DrawUpdate(f"fpc.f.{t0}", "x2_ms", end))
        if cfg.showZone:
            out.drawings.append(DrawUpdate(f"fpc.zp.{t0}", "x2_ms", end))
            out.drawings.append(DrawUpdate(f"fpc.zm.{t0}", "x2_ms", end))

    def _zone_dist(self, price: float) -> float:
        cfg = self.cfg
        if cfg.tpMode is TpMode.FIXED:
            return cfg.revTP.resolve(self.inst, price=price) * cfg.minPct / 100.0
        return cfg.minDist.resolve(self.inst, price=price)

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        local = datetime.fromtimestamp(bar.time / 1000, tz=NY)
        minute = local.hour * 60 + local.minute
        day = (local.year, local.month, local.day)
        news_today = self._news(bar, minute, day)   # priemer rozsahu z barov PRED týmto
        self.history.append(bar)
        idx = self.history.bar_index
        self._track(out, bar, ctx, idx)

        # ---- okno ------------------------------------------------------- #
        sid = self._window_id(minute, news_today)
        prev = self._sid
        self._sid = sid
        if sid != 0 and sid != prev:
            self._start_window(out, bar, sid, news_today)
        elif sid != 0:
            self._extend_window(out, bar)
        if sid == 0 and prev != 0:
            self._end_t = bar.time
        if minute == cfg.news_minutes and news_today and cfg.showFair:
            out.drawings.append(DrawLabel(FPC_NEWS, bar.time, self._pre_news,
                                          f"Správa — cena pred ňou {self._pre_news:g}", "#eab308",
                                          style=LabelStyle.LEFT, obj_id=f"fpc.n.{bar.time}"))
        if sid != 0:
            self._w_pv += (bar.high + bar.low + bar.close) / 3.0 * bar.volume
            self._w_vol += bar.volume
            self.vwap = self._w_pv / self._w_vol if self._w_vol > 0 else None
            if cfg.useTrend and cfg.showVwap and self.vwap is not None:
                end = bar.time + self.step_ms
                pt = self._vwap_pt
                if pt is None or (idx % _VWAP_EVERY == 0):
                    if pt is not None:
                        out.drawings.append(DrawLine(FPC_VWAP, pt[0], pt[1], end, self.vwap, _VWAP_COLOR,
                                                     obj_id=f"fpc.v.{end}", text="VWAP okna"))
                    self._vwap_pt = (end, self.vwap)

        # ---- signály (štruktúra sa sleduje stále) ------------------------ #
        bos_dn, bos_up = self._structure(bar)
        disp_dn, disp_up = self._displacement(bar)
        sig_dn = (cfg.useDisp and disp_dn) or (cfg.useBos and bos_dn)
        sig_up = (cfg.useDisp and disp_up) or (cfg.useBos and bos_up)
        if cfg.showSignals and sid != 0:
            for hit, long, txt in ((cfg.useDisp and disp_dn, False, "D"), (cfg.useDisp and disp_up, True, "D"),
                                   (cfg.useBos and bos_dn, False, "S"), (cfg.useBos and bos_up, True, "S")):
                if hit:
                    out.drawings.append(DrawLabel(
                        FPC_SIGNAL, bar.time, bar.low if long else bar.high, txt,
                        _LONG_COLOR if long else _SHORT_COLOR, style=LabelStyle.NONE, above=not long,
                        obj_id=f"fpc.s{txt}{'u' if long else 'd'}.{bar.time}"))

        # ---- zatvorenie po okne ------------------------------------------ #
        if ctx.position_size != 0.0:
            if (cfg.useCloseAfter and sid == 0 and self._end_t is not None
                    and bar.time - self._end_t >= cfg.closeAfter * 60_000):
                out.close_session = True
                for order_id in ctx.open_order_ids:
                    out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                                  reason=f"{cfg.closeAfter} min po konci okna"))
            return out
        if sid == 0 or self.fair is None or self._trade is not None:
            return out

        # ---- vstupy ------------------------------------------------------- #
        in_cont = 1 <= sid <= 4 and self._sess_t is not None and bar.time - self._sess_t < cfg.contWin * 60_000
        if not in_cont:
            self._cont_done = True
        if self.loss_row >= cfg.maxLossRow or self._n_trades >= cfg.maxTrades:
            return out
        if cfg.usePause and self._last_loss_t is not None and bar.time - self._last_loss_t < cfg.pauseMin * 60_000:
            return out

        price = bar.close
        long = short = False
        tp = sl = 0.0
        tag = ""
        if (cfg.useCont and in_cont and not self._cont_done and self._open_dir != 0
                and (not cfg.useBias or self.bias == self._open_dir)
                and (sig_up if self._open_dir == 1 else sig_dn)):
            long, short = self._open_dir == 1, self._open_dir == -1
            m = 2.0 if self._open_rng > cfg.bigBar.resolve(self.inst, price=price) else 1.0
            tp = cfg.contTP.resolve(self.inst, price=price) * m
            sl = cfg.contSL.resolve(self.inst, price=price) * m
            tag = "pokračovanie"
            self._cont_done = True
        elif cfg.useRev:
            dist = price - self.fair
            zone = self._zone_dist(price)
            rev_time = not cfg.useRevDel or bar.time - self._sess_t >= cfg.revDelay * 60_000
            trend = self.vwap - self.fair if cfg.useTrend and self.vwap is not None else 0.0
            trend_pts = cfg.trendPts.resolve(self.inst, price=price)
            max_d = cfg.maxDist.resolve(self.inst, price=price)
            if (sig_dn and dist > 0 and dist >= zone and rev_time
                    and not (cfg.useTrend and trend >= trend_pts)
                    and (not cfg.useMaxD or dist <= max_d) and (not cfg.useRevBias or self.bias == -1)):
                short = True
            elif (sig_up and dist < 0 and -dist >= zone and rev_time
                    and not (cfg.useTrend and -trend >= trend_pts)
                    and (not cfg.useMaxD or -dist <= max_d) and (not cfg.useRevBias or self.bias == 1)):
                long = True
            if long or short:
                sl = cfg.revSL.resolve(self.inst, price=price)
                tp = cfg.revTP.resolve(self.inst, price=price) if cfg.tpMode is TpMode.FIXED else abs(dist)
                tag = "návrat"
        if long and not cfg.allow_long or short and not cfg.allow_short or not (long or short):
            return out
        plan = self._plan(long, price, tp, sl)
        if plan is None:
            return out
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"fpc:{idx}", idx, direction=plan.direction, plan=plan,
                                      order_type=OrderType.MARKET,
                                      reason=f"{tag} — férová cena {self.fair:g} ({self._fair_src})"))
        self._trade = _Trade(long, plan.entry, plan.stop_loss, plan.take_profit, idx, bar.time)
        end = bar.time + self.step_ms
        for kind, level, color in ((DrawKind.TP_BOX, plan.take_profit, _LONG_COLOR),
                                   (DrawKind.SL_BOX, plan.stop_loss, _SHORT_COLOR)):
            out.drawings.append(DrawBox(kind, bar.time, max(plan.entry, level), end, min(plan.entry, level), color,
                                        fill_color=with_alpha(color, 80), obj_id=f"fpc.{kind[:2]}.{bar.time}",
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
        self._n_trades += 1
        out.drawings.append(DrawLabel(
            FPC_ENTRY, bar.time, bar.low if long else bar.high, f"{'LONG' if long else 'SHORT'} {tag}", "#ffffff",
            style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"fpc.e.{bar.time}"))
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
