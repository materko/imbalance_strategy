"""Engine SPRÁVY 3.0 — zlato po červených správach USA, pre každú správu vlastné pravidlo (`config.Rule`).

Čas: správy sú v kalendári v čase New York a prevádzajú sa na UTC pre každý deň zvlášť (`calendar.to_utc_ms`);
engine pracuje len s UTC, takže je jedno, kde beží platforma. Pre človeka (štítky na grafe) sa čas ukazuje
aj **slovensky** (`Europe/Bratislava`) — CPI 8:30 NY je bežne 14:30 SK, ale 13:30 SK v týždňoch, keď USA a
Slovensko menia čas v iné dni (marec; koniec októbra – začiatok novembra).

Priebeh na každom uzavretom bare grafu (čas konca baru `end`):

  1. **výstup v čase** — otvorená pozícia, ktorej uplynulo držanie pravidla (`rNHold`), sa zavrie trhom;
     prestávka CME 17:00–18:00 NY nič nerozbije — zavrie sa na prvom bare po čase výstupu,
  2. **noha** — pre každú dvojicu (správa, pravidlo), ktorej okno nohy [T+od, T+do) práve beží: začiatok nohy (open
     baru v T pri od = 0, inak close baru končiaceho v T+od — aj pred správou pri zápornom od), high / low nohy,
     koniec nohy = close baru končiaceho v T+do,
  3. **vstup** — na prvom bare, ktorý končí v T+vstup alebo neskôr: smer nohy (trend = v smere, fade = proti),
     market, stop `rNStop` × noha od vstupu alebo za extrémom nohy + `slBuffer`, cieľ `rNRR` × riziko (RRR) alebo bez cieľa;
     nedosiahnutý cieľ = výstup v čase.
     Jeden obchod naraz; keď chýbajú dáta (začiatok nohy) alebo je pozícia otvorená, pravidlo sa pre túto správu vynechá.

Engine je čistý: žiadne I/O, žiadny globálny stav (kalendár je dátový súbor balíka).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawKind, DrawLabel, DrawUpdate, LabelStyle, with_alpha
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup, rma_bars

from .calendar import events_utc
from .config import Rule, SpravyConfig
from .drawing import SP_ENTRY, SP_LEG

__all__ = ["SpravyEngine", "SK"]

SK = ZoneInfo("Europe/Bratislava")
NY = ZoneInfo("America/New_York")
_LONG = "#10b981"
_SHORT = "#ef4444"
_LEG = "#f59e0b"
_MIN = 60_000
_NO_TP_R = 1000.0


@dataclass
class _Ev:
    t: int            #: čas správy (UTC ms)
    typ: str
    rule: Rule
    a: int            #: začiatok nohy (UTC ms)
    b: int            #: koniec nohy (UTC ms)
    e: int            #: vstup (UTC ms)
    p0: float | None = None
    p1: float | None = None
    hi: float = float("-inf")
    lo: float = float("inf")
    done: bool = False

    @property
    def start(self) -> int:
        return min(self.a, self.t)


def sk_time(ms: int) -> str:
    """Čas pre človeka: slovensky aj New York (napr. „14:30 SK / 8:30 NY“)."""
    sk = datetime.fromtimestamp(ms / 1000, tz=SK)
    ny = datetime.fromtimestamp(ms / 1000, tz=NY)
    return f"{sk:%H:%M} SK / {ny.hour}:{ny:%M} NY"


class SpravyEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: SpravyConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * _MIN
        self.history = BarHistory(maxlen=4, atr_len=int(cfg.atrLen))
        self.warmup = Warmup(self.chart_tf_minutes).add(f"ATR {cfg.atrLen}", rma_bars(int(cfg.atrLen)) + 1)
        self.required_history = max(1, self.warmup.chart_bars)
        self.events: list[_Ev] = []
        for r in cfg.rules():
            for t, typ in events_utc({r.event}, cfg.newsAdd, cfg.newsSkip):
                self.events.append(_Ev(t, typ, r, t + r.frm * _MIN, t + r.to * _MIN, t + r.enter * _MIN))
        self.events.sort(key=lambda ev: (ev.start, ev.t, ev.rule.no))
        self.next_i = 0                       #: prvá správa, ktorá ešte nie je vybavená
        self.exit_ms: int | None = None       #: kedy zavrieť otvorenú pozíciu
        self.pending: str | None = None       #: id market vstupu, ktorý sa ešte nevyplnil
        self.pending_idx = -1
        self.boxes: list[str] = []
        self.was_in = False

    # ------------------------------------------------------------------ #

    def _plan(self, long: bool, close: float, ev: _Ev) -> TradePlan | None:
        cfg, inst = self.cfg, self.inst
        atr = self.history.atr
        mult = ev.rule.stop
        if mult > 0 and ev.p0 is not None and ev.p1 is not None:
            leg = abs(ev.p1 - ev.p0)
            stop = close - mult * leg if long else close + mult * leg
        else:
            buf = cfg.slBuffer.resolve(inst, price=close, atr=atr) if atr > 0 or cfg.slBuffer.unit != "atr" else 0.0
            stop = (ev.lo - buf) if long else (ev.hi + buf)
        risk = abs(close - stop)
        if risk < inst.tick_size * 2 or (long and stop >= close) or (not long and stop <= close):
            return None
        r_tp = ev.rule.rr if ev.rule.rr > 0 else _NO_TP_R
        take = close + r_tp * risk if long else close - r_tp * risk
        size_risk = max(risk, cfg.sizeMinRisk * atr) if cfg.sizeMinRisk > 0 and atr > 0 else risk
        qty = cfg.qty if cfg.fixedQty else inst.qty_for_risk(cfg.riskDollar, size_risk)
        if qty <= 0:
            qty = float(inst.min_qty or 1.0)
        return TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=inst.round_price(close),
                         stop_loss=inst.round_price(stop), take_profit=inst.round_price(take), qty=qty, sl_distance=risk)

    def _enter(self, out: EngineOutput, bar: Bar, ev: _Ev, idx: int) -> None:
        cfg = self.cfg
        if ev.p0 is None or ev.p1 is None or ev.p1 == ev.p0:
            return
        up = ev.p1 > ev.p0
        long = up if ev.rule.trend else not up
        if (long and not cfg.allowLong) or (not long and not cfg.allowShort):
            return
        atr = self.history.atr
        if cfg.minLeg.value > 0 and abs(ev.p1 - ev.p0) < cfg.minLeg.resolve(self.inst, price=bar.close, atr=atr):
            return
        plan = self._plan(long, bar.close, ev)
        if plan is None:
            return
        end = bar.time + self.step_ms
        oid = f"sp:{idx}"
        mode = ev.rule.label
        out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=plan.direction, plan=plan,
                                      order_type=OrderType.MARKET,
                                      reason=f"{ev.typ} {sk_time(ev.t)} · pravidlo {ev.rule.no}: {mode} "
                                             f"{'long' if long else 'short'} (noha {'hore' if up else 'dole'})"))
        self.pending = oid
        self.pending_idx = idx
        self.exit_ms = end + ev.rule.hold * _MIN
        x1 = end
        self.boxes = []
        self.was_in = False
        if cfg.showLegs:
            out.drawings.append(DrawBox(SP_LEG, ev.a, ev.hi, ev.b, ev.lo, _LEG, fill_color=with_alpha(_LEG, 35),
                                        obj_id=f"sp.leg.{ev.t}.{ev.rule.no}", text=f"{ev.typ} {sk_time(ev.t)}"))
        top_sl = (max(plan.entry, plan.stop_loss), min(plan.entry, plan.stop_loss))
        out.drawings.append(DrawBox(DrawKind.SL_BOX, x1, top_sl[0], x1 + self.step_ms, top_sl[1], _SHORT,
                                    fill_color=with_alpha(_SHORT, 60), obj_id=f"sp.sl.{x1}", text=f"SL {plan.stop_loss:g}"))
        self.boxes.append(f"sp.sl.{x1}")
        out.drawings.append(DrawLabel(SP_ENTRY, x1, plan.entry, f"{ev.typ} {mode} {'LONG' if long else 'SHORT'}", "#ffffff",
                                      style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=_LONG if long else _SHORT, obj_id=f"sp.e.{x1}"))

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        self.history.append(bar)
        idx = self.history.bar_index
        end = bar.time + self.step_ms
        flat = ctx.position_size == 0.0
        if self.pending is not None and (not flat or self.pending in ctx.open_order_ids):
            self.pending = None
        elif self.pending is not None and idx - self.pending_idx > 2:
            self.pending = None               # market vstup sa nevyplnil (predhistória, odmietnutý) — nečakať naň

        # ---- boxy bežiaceho obchodu --------------------------------------- #
        if self.boxes:
            for oid in self.boxes:
                out.drawings.append(DrawUpdate(oid, "x2_ms", end))
            if not flat:
                self.was_in = True
            elif self.was_in:
                self.boxes, self.was_in = [], False

        # ---- 1. výstup v čase --------------------------------------------- #
        if not flat and self.exit_ms is not None and end >= self.exit_ms:
            out.close_session = True
            for oid in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx, reason="koniec držania po správe"))
            self.exit_ms = None
        if flat and self.pending is None:
            self.exit_ms = None

        # ---- 2.–3. noha a vstup ------------------------------------------- #
        while self.next_i < len(self.events) and self.events[self.next_i].e + self.step_ms <= bar.time:
            self.next_i += 1                  # správa dávno prešla (diera v dátach, štart po nej)
        i = self.next_i
        while i < len(self.events) and self.events[i].start <= end:
            ev = self.events[i]
            if not ev.done:
                if ev.p0 is None:
                    if ev.a == ev.t and bar.time == ev.a:
                        ev.p0 = bar.open                   # od = 0: open baru, v ktorom správa vyšla
                    elif ev.a != ev.t and end == ev.a:
                        ev.p0 = bar.close                  # od > 0: zavretie baru končiaceho v T+od
                if ev.a <= bar.time and bar.time < ev.b:
                    ev.hi = max(ev.hi, bar.high)
                    ev.lo = min(ev.lo, bar.low)
                if end >= ev.b and ev.p1 is None and ev.p0 is not None:
                    ev.p1 = bar.close                      # koniec nohy: zavretie baru končiaceho v T+do
                if end >= ev.e:
                    ev.done = True
                    if flat and self.pending is None and not out.close_session:
                        self._enter(out, bar, ev, idx)
            i += 1
        while self.next_i < len(self.events) and self.events[self.next_i].done:
            self.next_i += 1
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
