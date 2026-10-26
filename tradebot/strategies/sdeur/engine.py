"""Engine SD ZÓNY EURUSD 1.0 — zóny na vyššom TF, limitka na hrane pri prvom návrate v okne vstupu.

Priebeh na každom uzavretom bare grafu:

  1. **vyplnenie** — čakajúca limitka sa vyplnila (pozícia alebo `open_order_ids`) → obchod, TP / SL box,
  2. **držanie** — pozícia otvorená dlhšie než `maxHoldHours` sa zavrie trhom,
  3. **dotyk** — zóna, ktorej bližšiu hranu bar dosiahol, je minutá (prvý návrat); zóna, ktorú bar zavrel
     za vzdialenejšou hranou alebo ktorá je staršia než `zoneMaxHours`, zanikne,
  4. **zóny** — bary grafu sa skladajú do sviečok `zoneTF` (zarovnané na epochu ako `tradebot.core.candles`);
     na uzavretej sviečke sa posunú kandidáti (prerazenie bázy → preč, odchod ≥ `depMin` → zóna)
     a z nej ako poslednej sviečky bázy (1–`baseMaxBars`) vzniknú noví kandidáti,
  5. **limitka** — bez pozície, keď sa ďalší bar otvára v okne vstupu: na najbližšiu nedotknutú zónu
     (vstup na hrane / v hĺbke `entryDepthPct`, stop za vzdialenejšou hranou + `slBuffer` + 1 tick, cieľ RR);
     mimo okna alebo pri inej najbližšej zóne sa zruší.

Engine je čistý: žiadne I/O, žiadny globálny stav. Zrkadlo v C#: `csharp/TradeBot.Strategies/SdEurNet`.
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
from tradebot.core.warmup import Warmup

from .config import SdEurConfig
from .drawing import SE_DEMAND, SE_ENTRY, SE_SUPPLY

__all__ = ["SdEurEngine"]

NY = ZoneInfo("America/New_York")
_LONG = "#10b981"
_SHORT = "#ef4444"
_HOUR_MS = 3_600_000


@dataclass
class _Zone:
    side: int              #: 1 = supply (short), -1 = demand (long)
    top: float
    bottom: float
    atr: float             #: ATR zóny na poslednej sviečke bázy
    base_end: int          #: index poslednej sviečky bázy (sviečky `zoneTF`)
    x1_ms: int             #: otvorenie prvej sviečky bázy
    ready_ms: int = 0
    obj_id: str = ""
    dead: bool = False
    touched: bool = False  #: dotknutá s čakajúcou limitkou v hĺbke zóny — inej limitke sa už neponúkne

    @property
    def proximal(self) -> float:
        return self.bottom if self.side == 1 else self.top

    @property
    def distal(self) -> float:
        return self.top if self.side == 1 else self.bottom


@dataclass
class _Cand:
    zone: _Zone
    q: int = 0             #: koľko sviečok `zoneTF` po báze už prešlo


class SdEurEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: SdEurConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.zone_ms = max(int(cfg.zoneTF), self.chart_tf_minutes) * 60_000
        ratio = max(1, self.zone_ms // self.step_ms)
        self.history = BarHistory(maxlen=4, atr_len=14)
        need = int(cfg.atrLen) * 3 + int(cfg.extremeBars) + int(cfg.baseMaxBars) + 2
        self.warmup = Warmup(self.chart_tf_minutes).add(f"zóny {cfg.zoneTF}m (ATR {cfg.atrLen} + báza)", need * ratio)
        self.required_history = max(1, self.warmup.chart_bars)
        # sviečky zoneTF: (open_ms, high, low, close)
        self.zb: list[tuple[int, float, float, float]] = []
        self.zidx = -1                       #: index poslednej uzavretej sviečky zoneTF
        self.cur: list[float] | None = None  #: rozpracovaná sviečka [open_ms, o, h, l, c]
        self.zatr = 0.0
        self.prev_close: float | None = None
        self.cands: list[_Cand] = []
        self.zones: list[_Zone] = []
        self.pending: tuple[str, int, _Zone, TradePlan] | None = None
        self.pending_ms = 0
        self.fill_ms: int | None = None
        self.boxes: list[str] = []
        self.was_in = False
        self.day = None
        self.trades = 0

    # ------------------------------------------------------------------ #

    def _ny_minutes(self, ms: int) -> int:
        t = datetime.fromtimestamp(ms / 1000, tz=NY)
        return t.hour * 60 + t.minute

    @staticmethod
    def _in(m: int, a: int, b: int) -> bool:
        return a <= m < b if a < b else (m >= a or m < b)

    def _close_zone(self, out: EngineOutput, z: _Zone, bar: Bar) -> None:
        z.dead = True
        if z.obj_id:
            out.drawings.append(DrawUpdate(z.obj_id, "x2_ms", bar.time + self.step_ms))

    # ---- sviečky zoneTF ---------------------------------------------------- #

    def _feed_zone_bar(self, bar: Bar) -> bool:
        """Pridá bar grafu do sviečky zoneTF; True, keď sa sviečka práve uzavrela."""
        bucket = bar.time // self.zone_ms * self.zone_ms
        closed = False
        if self.cur is not None and int(self.cur[0]) != bucket:
            self._push_zone_bar()               # diera v dátach: predošlá sviečka sa uzavrie až teraz
            closed = True
        if self.cur is None:
            self.cur = [bucket, bar.open, bar.high, bar.low, bar.close]
        else:
            self.cur[2] = max(self.cur[2], bar.high)
            self.cur[3] = min(self.cur[3], bar.low)
            self.cur[4] = bar.close
        if bar.time + self.step_ms >= bucket + self.zone_ms:
            self._push_zone_bar()
            closed = True
        return closed

    def _push_zone_bar(self) -> None:
        t, _o, h, l, c = self.cur
        pc = self.prev_close if self.prev_close is not None else c
        tr = max(h - l, abs(h - pc), abs(l - pc))
        if self.zidx < 0:
            self.zatr = h - l
        else:
            self.zatr += (tr - self.zatr) / int(self.cfg.atrLen)
        self.prev_close = c
        self.zb.append((int(t), h, l, c))
        keep = int(self.cfg.extremeBars) + int(self.cfg.baseMaxBars) + 4
        if len(self.zb) > keep:
            del self.zb[: len(self.zb) - keep]
        self.zidx += 1
        self.cur = None

    def _zone_events(self, out: EngineOutput, bar: Bar) -> None:
        """Na uzavretej sviečke zoneTF: posun kandidátov (potvrdenie / zánik) a noví kandidáti z bázy."""
        cfg, inst = self.cfg, self.inst
        _t, h, l, _c = self.zb[-1]
        alive: list[_Cand] = []
        confirmed: set[tuple[int, int]] = set()
        for c in self.cands:
            z = c.zone
            c.q += 1
            if (h > z.top) if z.side == 1 else (l < z.bottom):
                continue                                    # báza prerazená skôr, než cena odišla
            dep = cfg.depMin.resolve(inst, price=bar.close, atr=z.atr)
            if ((z.bottom - l) if z.side == 1 else (h - z.top)) >= dep:
                key = (z.base_end, z.side)
                if key not in confirmed:                    # z jednej bázy jedna zóna na stranu (najkratšia báza)
                    confirmed.add(key)
                    self._confirm(out, z, bar)
                continue
            if c.q < int(cfg.depMaxBars):
                alive.append(c)
        self.cands = alive
        self._new_candidates(bar)

    def _confirm(self, out: EngineOutput, z: _Zone, bar: Bar) -> None:
        z.ready_ms = bar.time + self.step_ms
        self.zones.append(z)
        if self.cfg.showZones:
            color = _SHORT if z.side == 1 else _LONG
            z.obj_id = f"se.z.{z.x1_ms}.{z.side}.{z.top:g}"
            x2 = z.ready_ms + int(self.cfg.zoneMaxHours) * _HOUR_MS
            out.drawings.append(DrawBox(SE_SUPPLY if z.side == 1 else SE_DEMAND, z.x1_ms, z.top, x2, z.bottom, color,
                                        fill_color=with_alpha(color, 40), obj_id=z.obj_id,
                                        text=f"{'supply' if z.side == 1 else 'demand'} {self.cfg.zoneTF}m"))

    def _new_candidates(self, bar: Bar) -> None:
        cfg, inst = self.cfg, self.inst
        n = len(self.zb)
        a = self.zatr
        if a <= 0:
            return
        if cfg.useFormWindow:
            hour = self._ny_minutes(self.zb[-1][0]) // 60
            if not self._in(hour, int(cfg.formStartH), int(cfg.formEndH)):
                return
        max_h = cfg.baseMax.resolve(inst, price=bar.close, atr=a)
        min_zh = cfg.minZoneHeight.resolve(inst, price=bar.close, atr=a)
        max_zh = cfg.maxZoneHeight.resolve(inst, price=bar.close, atr=a)
        ext = int(cfg.extremeBars)
        for k in range(1, int(cfg.baseMaxBars) + 1):
            if n < k + max(ext, 1) or self.zidx + 1 < k + ext:
                break
            base = self.zb[n - k:]
            bh = max(b[1] for b in base)
            bl = min(b[2] for b in base)
            height = bh - bl
            if height < 2 * inst.tick_size or height > max_h:
                continue
            if (min_zh > 0 and height < min_zh) or (max_zh > 0 and height > max_zh):
                continue
            before = self.zb[n - k - ext:n - k] if ext > 0 else []
            for side in (1, -1):
                if side == 1 and not cfg.allowShort or side == -1 and not cfg.allowLong:
                    continue
                if before and ((bh < max(b[1] for b in before)) if side == 1 else (bl > min(b[2] for b in before))):
                    continue
                self.cands.append(_Cand(_Zone(side, bh, bl, a, self.zidx, base[0][0])))

    # ---- obchod ------------------------------------------------------------- #

    def _plan(self, z: _Zone, close: float) -> TradePlan | None:
        cfg, inst = self.cfg, self.inst
        long = z.side == -1
        height = z.top - z.bottom
        depth = height * float(cfg.entryDepthPct) / 100.0
        entry = z.proximal + depth if z.side == 1 else z.proximal - depth
        buf = cfg.slBuffer.resolve(inst, price=close, atr=z.atr) + inst.tick_size
        stop = z.distal + buf if z.side == 1 else z.distal - buf
        risk = abs(entry - stop)
        if risk < inst.tick_size * 2:
            return None
        take = entry + cfg.rrRatio * risk if long else entry - cfg.rrRatio * risk
        qty = cfg.qty if cfg.fixedQty else inst.qty_for_risk(cfg.riskDollar, risk)
        if qty <= 0:
            qty = float(inst.min_qty or 1.0)
        return TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=inst.round_price(entry),
                         stop_loss=inst.round_price(stop), take_profit=inst.round_price(take),
                         qty=qty, sl_distance=risk)

    def _filled(self, out: EngineOutput, bar: Bar) -> None:
        oid, at, z, plan = self.pending
        self.pending = None
        self.trades += 1
        self.fill_ms = bar.time
        long = plan.direction is Direction.LONG
        self.boxes, self.was_in = [], False
        x1, end = self.pending_ms, bar.time + self.step_ms
        for kind, level, color in ((DrawKind.TP_BOX, plan.take_profit, _LONG), (DrawKind.SL_BOX, plan.stop_loss, _SHORT)):
            bid = f"se.{kind[:2]}.{x1}"
            out.drawings.append(DrawBox(kind, x1, max(plan.entry, level), end, min(plan.entry, level), color,
                                        fill_color=with_alpha(color, 60), obj_id=bid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self.boxes.append(bid)
        out.drawings.append(DrawLabel(SE_ENTRY, x1, plan.entry, "LONG zóna" if long else "SHORT zóna", "#ffffff",
                                      style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=_LONG if long else _SHORT, obj_id=f"se.e.{x1}"))
        if not z.dead:
            self._close_zone(out, z, bar)

    def _cancel(self, out: EngineOutput, reason: str) -> None:
        oid, at, _z, _p = self.pending
        out.orders.append(OrderIntent(OrderAction.CANCEL, oid, at, reason=reason))
        self.pending = None

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index
        pos = ctx.position_size
        day = datetime.fromtimestamp(bar.time / 1000, tz=NY).date()
        if day != self.day:
            self.day, self.trades = day, 0

        # ---- TP / SL boxy bežiaceho obchodu ---------------------------------- #
        if self.boxes:
            for oid in self.boxes:
                out.drawings.append(DrawUpdate(oid, "x2_ms", bar.time + self.step_ms))
            if pos != 0.0:
                self.was_in = True
            elif self.was_in:
                self.boxes, self.was_in = [], False

        # ---- 1. vyplnenie limitky --------------------------------------------- #
        if self.pending is not None and (pos != 0.0 or self.pending[0] in ctx.open_order_ids):
            self._filled(out, bar)
        if pos == 0.0:
            self.fill_ms = None

        # ---- 2. najdlhšie držanie --------------------------------------------- #
        if (pos != 0.0 and cfg.maxHoldHours > 0 and self.fill_ms is not None
                and bar.time + self.step_ms - self.fill_ms >= int(cfg.maxHoldHours) * _HOUR_MS):
            out.close_session = True
            for oid in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx, reason=f"drží sa {cfg.maxHoldHours} h"))
            self.fill_ms = None

        # ---- 3. dotyk, zánik a vek zón --------------------------------------- #
        live: list[_Zone] = []
        for z in self.zones:
            if z.dead:
                continue
            touched = (bar.high >= z.proximal) if z.side == 1 else (bar.low <= z.proximal)
            through = (bar.close > z.top) if z.side == 1 else (bar.close < z.bottom)
            old = bar.time + self.step_ms - z.ready_ms > int(cfg.zoneMaxHours) * _HOUR_MS
            mine = self.pending is not None and self.pending[2] is z
            if touched and mine:
                z.touched = True
            if through or old or (touched and not mine):
                self._close_zone(out, z, bar)
                if mine:
                    self._cancel(out, "zóna prerazená" if through else "zóna vypršala")
                continue
            live.append(z)
        self.zones = live

        # ---- 4. nové zóny ---------------------------------------------------- #
        if self._feed_zone_bar(bar):
            self._zone_events(out, bar)

        # ---- 5. limitka na najbližšiu zónu ----------------------------------- #
        if pos == 0.0 and not out.close_session:
            nxt = self._ny_minutes(bar.time + self.step_ms)
            in_win = self._in(nxt, cfg.entry_start, cfg.entry_end)
            limit_ok = int(cfg.maxTradesPerDay) <= 0 or self.trades < int(cfg.maxTradesPerDay)
            best = None
            if in_win and limit_ok:
                cands = [z for z in self.zones if not z.dead and not z.touched and z.ready_ms <= bar.time + self.step_ms]
                if self.pending is not None and not self.pending[2].dead and self.pending[2].touched:
                    cands = [self.pending[2]]
                if cands:
                    best = min(cands, key=lambda z: (abs(z.proximal - bar.close), z.ready_ms))
            if self.pending is not None and self.pending[2] is not best:
                self._cancel(out, "mimo okna vstupu" if not in_win else "bližšia zóna")
            if best is not None and self.pending is None:
                plan = self._plan(best, bar.close)
                if plan is None:
                    self._close_zone(out, best, bar)
                    self.zones = [z for z in self.zones if z is not best]
                else:
                    oid = f"se:{idx}"
                    out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=plan.direction, plan=plan,
                                                  order_type=OrderType.LIMIT,
                                                  reason=f"{'supply' if best.side == 1 else 'demand'} zóna {cfg.zoneTF}m"))
                    self.pending = (oid, idx, best, plan)
                    self.pending_ms = bar.time
        elif self.pending is not None and pos != 0.0:
            self.pending = None
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
