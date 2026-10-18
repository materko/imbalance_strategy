"""Engine NOC + PONDELOK 1.0 — nočný drift Nasdaqu a pondelok, len nad SMA denných zavretí.

Priebeh (na každom uzavretom bare grafu, čas New York podľa ZAVRETIA baru; „bar v čase T“ = prvý bar,
ktorého zavretie je T alebo neskôr, ten istý deň):

  1. **denné zavretie**: bar v čase `closeRefH:M` (15:55) pridá close do SMA `smaLen` dní; trend = close > SMA,
  2. **výstup**: pozícia sa zatvorí na prvom bare, ktorý sa zavrie v termíne výstupu alebo po ňom
     (noc: `nightExitH:M` nasledujúci obchodný deň, piatok → pondelok; pondelok: `monExitH:M` ten deň),
     pondelková pozícia sa v čase nočného vstupu len predĺži do rána, keď nočný vstup platí,
  3. **noc**: bar v čase `nightEntryH:M` po–pi, trend (pri `useTrend`), mimo okna rollu → long market,
  4. **pondelok**: bar v čase `monEntryH:M` v pondelok, posledný známy trend (piatkový) → long market.

SMA potrebuje `smaLen` dní pred behom; dostane ich cez seeding z 5m barov pred začiatkom (`Warmup.add_seeded`),
takže výsledok nezávisí od toho, kde beh začína. Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawKind, DrawLabel, DrawLine, LabelStyle, with_alpha
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .config import NocPonConfig
from .drawing import NP_ENTRY, NP_SMA

__all__ = ["NocPonEngine"]

NY = ZoneInfo("America/New_York")
_LONG = "#10b981"
_SHORT = "#ef4444"
_SMA = "#a78bfa"
#: bez stopu: poistka 10 % (prakticky sa nedosiahne), cieľ 100 R — výstup je v čase
_FAR_STOP = 0.10
_NO_TP_R = 100.0
_SEED_TF = 5
_QUARTER_MONTHS = (3, 6, 9, 12)


def _crossed(prev_end: datetime | None, end: datetime, target: int) -> bool:
    """Bar končiaci v `end` je prvý v deň `end` so zavretím v čase `target` (min od polnoci) alebo neskôr."""
    cmin = end.hour * 60 + end.minute
    if cmin < target:
        return False
    if prev_end is None or prev_end.date() != end.date():
        return True
    return prev_end.hour * 60 + prev_end.minute < target


class NocPonEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: NocPonConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.history = BarHistory(maxlen=4, atr_len=14)
        self.closes: deque[float] = deque(maxlen=int(cfg.smaLen))
        self.trend: bool = False
        self.sma: float | None = None
        self._prev_end: datetime | None = None
        self._seed_prev_end: datetime | None = None
        #: termín výstupu otvorenej / práve zadanej pozície (ms) a jej druh ("noc" / "pon")
        self.deadline: int | None = None
        self.kind: str | None = None
        days = int(cfg.smaLen) + 10
        self.warmup = Warmup(self.chart_tf_minutes).add_seeded(
            f"SMA {cfg.smaLen} denných zavretí (5m)", days * 1440 // _SEED_TF, _SEED_TF, self._seed)
        self.required_history = max(1, self.warmup.chart_bars)

    # ------------------------------------------------------------------ #

    def _add_close(self, close: float) -> None:
        self.closes.append(close)
        if len(self.closes) >= int(self.cfg.smaLen):
            self.sma = sum(self.closes) / len(self.closes)
            self.trend = close > self.sma
        else:
            self.sma, self.trend = None, False

    def _seed(self, closed: Sequence[Bar], partial: Bar | None) -> None:
        """Denné zavretia z 5m barov pred behom (rovnaké pravidlo ako na grafe)."""
        for b in closed:
            end = datetime.fromtimestamp((b.time + _SEED_TF * 60_000) / 1000, tz=NY)
            if end.weekday() < 5 and _crossed(self._seed_prev_end, end, self.cfg.close_ref):
                self._add_close(b.close)
            self._seed_prev_end = end

    def _trend_ok(self) -> bool:
        return (not self.cfg.useTrend) or self.trend

    def _roll_window(self, d: date) -> bool:
        cfg = self.cfg
        return cfg.skipRoll and d.month in _QUARTER_MONTHS and cfg.rollFromDay <= d.day <= cfg.rollToDay

    @staticmethod
    def _next_weekday(d: date) -> date:
        n = d + timedelta(days=1)
        while n.weekday() >= 5:
            n += timedelta(days=1)
        return n

    def _night_deadline(self, end: datetime) -> int:
        cfg = self.cfg
        d = end.date() if cfg.night_exit > cfg.night_entry else self._next_weekday(end.date())
        t = datetime(d.year, d.month, d.day, cfg.nightExitH, cfg.nightExitM, tzinfo=NY)
        return int(t.timestamp() * 1000)

    def _mon_deadline(self, end: datetime) -> int:
        d = end.date()
        return int(datetime(d.year, d.month, d.day, self.cfg.monExitH, self.cfg.monExitM, tzinfo=NY).timestamp() * 1000)

    def _night_ok(self, end: datetime) -> bool:
        cfg = self.cfg
        return (cfg.useNight and end.weekday() < 5 and _crossed(self._prev_end, end, cfg.night_entry)
                and self._trend_ok() and not self._roll_window(end.date()))

    def _plan(self, entry: float) -> TradePlan | None:
        cfg = self.cfg
        pct = cfg.stopPct / 100.0 if cfg.stopPct > 0 else _FAR_STOP
        sl = entry * pct
        if sl < self.inst.tick_size:
            return None
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, sl)
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=Direction.LONG, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(entry - sl), take_profit=self.inst.round_price(entry + sl * _NO_TP_R),
                         qty=qty, sl_distance=sl)

    def _enter(self, out: EngineOutput, bar: Bar, idx: int, kind: str, deadline: int) -> None:
        plan = self._plan(bar.close)
        if plan is None:
            return
        cfg = self.cfg
        what = (f"noc {cfg.nightEntryH}:{cfg.nightEntryM:02d} → {cfg.nightExitH}:{cfg.nightExitM:02d}" if kind == "noc"
                else f"pondelok {cfg.monEntryH}:{cfg.monEntryM:02d} → {cfg.monExitH}:{cfg.monExitM:02d}")
        trend = f", nad SMA {cfg.smaLen} ({self.sma:.2f})" if cfg.useTrend and self.sma is not None else ""
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"np:{idx}", idx, direction=Direction.LONG, plan=plan,
                                      order_type=OrderType.MARKET, reason=what + trend))
        self.deadline, self.kind = deadline, kind
        # boxy od signálu po termín výstupu; bez stopu / cieľa sú len na orientáciu (1 R)
        for k, top, bot, color, txt in ((DrawKind.TP_BOX, plan.entry + plan.sl_distance, plan.entry, _LONG, "výstup v čase"),
                                        (DrawKind.SL_BOX, plan.entry, plan.stop_loss, _SHORT,
                                         f"SL {plan.stop_loss:g}" if cfg.stopPct > 0 else "bez stopu (poistka 10 %)")):
            out.drawings.append(DrawBox(k, bar.time, top, deadline, bot, color, fill_color=with_alpha(color, 60),
                                        obj_id=f"np.{k[:2]}.{bar.time}", text=txt))
        out.drawings.append(DrawLabel(NP_ENTRY, bar.time, bar.low, "NOC" if kind == "noc" else "PONDELOK", "#ffffff",
                                      style=LabelStyle.UP, above=False, bg_color=_LONG, obj_id=f"np.e.{bar.time}"))

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        end_ms = bar.time + self.step_ms
        end = datetime.fromtimestamp(end_ms / 1000, tz=NY)
        flat = ctx.position_size == 0.0

        # ---- 1. denné zavretie a SMA -------------------------------------- #
        if end.weekday() < 5 and _crossed(self._prev_end, end, cfg.close_ref):
            self._add_close(bar.close)
            if cfg.showSma and self.sma is not None:
                out.drawings.append(DrawLine(NP_SMA, bar.time, self.sma, end_ms, self.sma, _SMA, width=2,
                                             obj_id=f"np.s.{bar.time}", text=f"SMA {cfg.smaLen}"))

        # ---- 2. výstup / predĺženie -------------------------------------- #
        if flat and self.deadline is not None and end_ms >= self.deadline:
            self.deadline = self.kind = None              # pozícia skončila stopom alebo sa nevyplnila
        if not flat and self.deadline is not None and end_ms >= self.deadline:
            if self.kind == "pon" and self._night_ok(end):
                self.deadline, self.kind = self._night_deadline(end), "noc"   # pondelok plynulo do noci
            else:
                out.close_session = True
                for order_id in ctx.open_order_ids:
                    out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                                  reason=f"výstup v čase ({'noc' if self.kind == 'noc' else 'pondelok'})"))
                self.deadline = self.kind = None
                self._prev_end = end
                return out
        if not flat:
            self._prev_end = end
            return out

        # ---- 3. noc ------------------------------------------------------- #
        if self._night_ok(end):
            self._enter(out, bar, idx, "noc", self._night_deadline(end))
        # ---- 4. pondelok -------------------------------------------------- #
        elif (cfg.useMonday and end.weekday() == 0 and _crossed(self._prev_end, end, cfg.mon_entry)
              and end.hour * 60 + end.minute < cfg.mon_exit and self._trend_ok()):
            self._enter(out, bar, idx, "pon", self._mon_deadline(end))
        self._prev_end = end
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
