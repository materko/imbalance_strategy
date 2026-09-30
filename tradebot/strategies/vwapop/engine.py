"""Engine VWAP OP: prvý pullback k VWAP v smere driftu na vyššom TF.

Doslovný port Pine skriptu (`docs/sources/vwap_op.pine`). Priebeh jedného obchodného dňa:

  1. **VWAP** sa počíta od 9:30 New York (`rthSess`) z barov HTF (`htf`, štandardne 15m)
     zložených z barov grafu — `tradebot.core.vwap.SessionVwap`. Hodnota, ktorú vidí
     tento bar, je vždy posledná UZAVRETÁ HTF perióda (žiadny repaint, zodpovedá Pine
     `v[1]` cez `request.security(..., lookahead_on)`).
  2. **drift** = zmena VWAP za posledné `driftLen` HTF periódy, porovnaná s prahom
     `driftAtr` × **ATR HTF** (`_Htf15.atr`) — nie ATR grafu. Tento ATR aj `close` HTF
     (`needSide`) sú v Pine **spojité**, nezávislé od `rthSess` (`ta.atr(14)` na "15" beží
     na celom sériovom rade, nielen v RTH) — preto sú v `_Htf15` bez seansovej brány,
     na rozdiel od `SessionVwap`, ktorý sa každý deň nuluje.
  3. `bias` (smer dňa) sa počíta **nanovo na každom bare** — na rozdiel od `vwapdrift` sa
     nedrží posledný jasný smer: keď drift padne pod prah, `bias` je hneď 0.
  4. **pullback** = low baru (short: high) príde k VWAP bližšie než `tolAtr` × ATR grafu.
     Vstup je market na zavretí toho istého baru (`needClose`: musí zavrieť späť na
     strane driftu). Žiadne čakanie na potvrdzovaciu sviečku ani limitky/stopy — jediný
     druh vstupu, aký skript má.
  5. **arming**: bar musí byť pred pullbackom celý mimo tolerancie (`low > vwap+tol`
     pre long) — to je "odchod od VWAP" tohto skriptu, vyhodnocuje sa na konci baru
     (nabudúce platí pre dotyk). `firstOnly` uzamkne smer na zvyšok dňa po prvom
     pullbacku (obchodovanom aj nie), `maxTrades` je spoločný strop na oba smery.
  6. stop = VWAP ∓ `slAtr` × ATR grafu (pevný, nie za extrém pullbacku), cieľ `rr` × riziko.
     `useBE`: jednorazový (nie kontinuálny) posun SL na vstup po dosiahnutí +1R —
     `_BreakevenPlan`.
  7. `closeEOD` zatvorí pozíciu v okne `flatTime` (predvolene vypnuté — pozícia môže
     ostať otvorená aj cez noc, presne ako v skripte).

Engine je čistý: žiadne I/O, žiadny globálny stav, všetko je v ``self``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawKind, DrawLabel, DrawLine, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan, TrailingPlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.vwap import SessionVwap
from tradebot.core.warmup import Warmup

from .config import VwapOpConfig, parse_session
from .drawing import VOP_ENTRY, VOP_VWAP

__all__ = ["VwapOpEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_NY = "America/New_York"
#: Ako ďaleko dopredu siaha TP/SL box — len čitateľnosť grafu.
_BOX_BARS = 30


class _Htf15:
    """Spojitý Wilderov ATR(14) na HTF (`cfg.htf` minút) zloženom z barov grafu.

    Bez ohľadu na seansu — presne ako Pine `request.security(ticker, htf, ta.atr(14))`,
    ktorý beží na celom sériovom rade, nie je to seansový indikátor ako `SessionVwap`.
    Bucket sa uzatvára kalendárovo (`bar.time // period_ms`), takže na štandardných
    burzách (UTC dáta) sedí s HTF sviečkami, aké vidí Pine.
    """

    def __init__(self, chart_step_ms: int, period_minutes: int, atr_len: int = 14) -> None:
        self.step_ms = chart_step_ms
        self.period_ms = max(1, int(period_minutes)) * 60_000
        self.history = BarHistory(maxlen=atr_len + 64, atr_len=atr_len)
        self._bucket: list | None = None  # [idx, open, high, low, close, open_time]

    def push(self, bar: Bar) -> None:
        idx = bar.time // self.period_ms
        b = self._bucket
        if b is not None and b[0] != idx:
            self._flush()
            b = None
        if b is None:
            b = [idx, bar.open, bar.high, bar.low, bar.close, idx * self.period_ms]
        else:
            b[2] = max(b[2], bar.high)
            b[3] = min(b[3], bar.low)
            b[4] = bar.close
        self._bucket = b
        if (bar.time + self.step_ms) // self.period_ms != idx:
            self._flush()

    def _flush(self) -> None:
        b = self._bucket
        if b is not None:
            self.history.append(Bar(b[5], b[1], b[2], b[3], b[4], 0.0))
        self._bucket = None

    @property
    def atr(self) -> float:
        return self.history.atr

    @property
    def last_close(self) -> float | None:
        return self.history[0].close if len(self.history) else None


@dataclass(frozen=True, slots=True)
class _BreakevenPlan(TrailingPlan):
    """Raz posunie SL na cenu vstupu, len čo zisk dosiahne +1R, a tam zamrzne.

    Nie je to kontinuálny trailing (Pine `useBE`: `if high >= entryRef + 1R:
    slPrice := entryRef`, ďalej sa už nehýbe) — preto vlastný `stop_price` namiesto
    základného `TrailingPlan`, ktorý by stop ťahal aj za breakeven.
    """

    def stop_price(self, direction: Direction, entry: float, base_stop: float, extreme: float) -> float:
        if direction is Direction.LONG:
            if extreme - entry >= self.activation_price_distance:
                return max(base_stop, entry)
            return base_stop
        if entry - extreme >= self.activation_price_distance:
            return min(base_stop, entry)
        return base_stop


@dataclass
class _DayState:
    """Stav jedného obchodného dňa."""

    day: tuple[int, int, int] | None = None
    armed_long: bool = False
    armed_short: bool = False
    #: prvý pullback v tom smere už bol (obchodovaný alebo nie) — uzamkne smer pri `firstOnly`
    done_long: bool = False
    done_short: bool = False
    #: obchody dňa, oba smery spolu — strop `maxTrades`
    n_day: int = 0

    def reset(self, day: tuple[int, int, int]) -> None:
        self.day = day
        self.armed_long = self.armed_short = False
        self.done_long = self.done_short = False
        self.n_day = 0


class VwapOpEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: VwapOpConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.zone = ZoneInfo(_NY)

        self.rth_start, self.rth_end = parse_session(cfg.rthSess)
        self.win_start, self.win_end = parse_session(cfg.tradeWin)
        self.flat_start, self.flat_end = parse_session(cfg.flatTime)

        htf_minutes = int(cfg.htf)
        drift_len = int(cfg.driftLen)
        self.vwap = SessionVwap(self.chart_tf_minutes, start_minutes=self.rth_start,
                                end_minutes=self.rth_end, tz=_NY, period_minutes=htf_minutes,
                                keep=drift_len + 4)
        self._htf = _Htf15(self.step_ms, htf_minutes, atr_len=14)

        #: predhistória grafu: ATR grafu — VWAP a HTF sa počítajú od nuly / spojito samy
        self.warmup = Warmup(self.chart_tf_minutes).add("ATR 14 (graf)", 14 + 16)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=max(self.required_history, 32) + 16, atr_len=14)

        self._state = _DayState()
        #: posledný nakreslený bod čiary VWAP (čas, hodnota, deň) — úsečka sa kreslí z neho
        self._last_point: tuple[int, float, tuple[int, int, int] | None] | None = None

    # ------------------------------------------------------------------ #

    def _plan(self, direction: Direction, entry: float, vwap15: float, atr_c: float) -> TradePlan | None:
        cfg = self.cfg
        long = direction is Direction.LONG
        sl_dist_raw = cfg.slAtr.resolve(self.inst, price=entry, atr=atr_c)
        if sl_dist_raw <= 0:
            return None
        stop = vwap15 - sl_dist_raw if long else vwap15 + sl_dist_raw
        if (stop >= entry) if long else (stop <= entry):
            return None
        sl_distance = abs(entry - stop)
        if sl_distance < self.inst.tick_size * 2:
            return None
        min_sl = cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr_c)
        if min_sl > 0 and sl_distance < min_sl:
            return None
        take = entry + sl_distance * cfg.rr if long else entry - sl_distance * cfg.rr
        qty = cfg.position_qty(self.inst, cfg.riskDollar, sl_distance) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        trailing = None
        if cfg.useBE:
            tick = self.inst.tick_size or 0.0
            trailing = _BreakevenPlan(
                activation_price_distance=sl_distance, offset_price_distance=0.0,
                activation_ticks=(sl_distance / tick if tick else 0.0), offset_ticks=0.0)
        return TradePlan(
            direction=direction, entry=self.inst.round_price(entry),
            stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
            qty=qty, sl_distance=sl_distance, trailing=trailing,
        )

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        st = self._state

        self.history.append(bar)
        atr_c = self.history.atr
        idx = self.history.bar_index

        self._htf.push(bar)
        vwap15 = self.vwap.push(bar)
        updated = self.vwap.updated

        local = datetime.fromtimestamp(bar.time / 1000, tz=self.zone)
        day = (local.year, local.month, local.day)
        minutes = local.hour * 60 + local.minute
        if day != st.day:
            st.reset(day)

        # ---- drift na HTF (spojitý ATR, nezávislý od RTH) ---------------- #
        atr15 = self._htf.atr
        bias = 0
        if vwap15 is not None and atr15 > 0:
            drift15 = self.vwap.change(int(cfg.driftLen))
            if drift15 is not None:
                thr = cfg.driftAtr.resolve(self.inst, price=vwap15, atr=atr15)
                close15 = self._htf.last_close
                if drift15 > thr and (not cfg.needSide or (close15 is not None and close15 > vwap15)):
                    bias = 1
                elif drift15 < -thr and (not cfg.needSide or (close15 is not None and close15 < vwap15)):
                    bias = -1

        if cfg.showCross and updated and vwap15 is not None:
            out.drawings += self._vwap_drawing(bar, vwap15, bias)

        # ---- koniec seansy (nezávisle od VWAP/ATR grafu) ------------------ #
        in_flat = self.flat_start <= minutes < self.flat_end
        if cfg.closeEOD and in_flat and ctx.position_size != 0.0:
            out.close_session = True
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx, reason="koniec seansy"))

        if atr_c <= 0 or vwap15 is None:
            return out

        tol = cfg.tolAtr.resolve(self.inst, price=bar.close, atr=atr_c)
        touch_long = bar.low <= vwap15 + tol and (not cfg.needClose or bar.close > vwap15)
        touch_short = bar.high >= vwap15 - tol and (not cfg.needClose or bar.close < vwap15)

        in_win = self.win_start <= minutes < self.win_end
        flat = ctx.position_size == 0.0
        max_trades = int(cfg.maxTrades)
        long_sig = (cfg.allowLong and flat and in_win and bias == 1 and st.armed_long and touch_long
                    and not (cfg.firstOnly and st.done_long) and st.n_day < max_trades)
        short_sig = (cfg.allowShort and flat and in_win and bias == -1 and st.armed_short and touch_short
                     and not (cfg.firstOnly and st.done_short) and st.n_day < max_trades)

        if long_sig:
            self._enter(out, idx, bar, Direction.LONG, vwap15, atr_c)
        elif short_sig:
            self._enter(out, idx, bar, Direction.SHORT, vwap15, atr_c)

        # ---- arming — z AKTUÁLNEHO baru, platí pre dotyk na ďalšom -------- #
        if bar.low > vwap15 + tol:
            st.armed_long = True
        if bar.high < vwap15 - tol:
            st.armed_short = True

        return out

    # ------------------------------------------------------------------ #

    def _enter(self, out: EngineOutput, idx: int, bar: Bar, direction: Direction, vwap15: float,
               atr_c: float) -> None:
        plan = self._plan(direction, bar.close, vwap15, atr_c)
        if plan is None:
            return
        order_id = f"vop:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=direction, plan=plan,
                                      order_type=OrderType.MARKET,
                                      reason="pullback k VWAP v smere driftu (HTF)"))
        st = self._state
        if direction is Direction.LONG:
            st.done_long = True
            st.armed_long = False
        else:
            st.done_short = True
            st.armed_short = False
        st.n_day += 1
        long = direction is Direction.LONG
        out.drawings.append(DrawLabel(
            VOP_ENTRY, bar.time, bar.low if long else bar.high, "LONG" if long else "SHORT",
            "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"vop_entry.{bar.time}",
        ))
        out.drawings += self._trade_boxes(bar, plan)

    def _trade_boxes(self, bar: Bar, plan: TradePlan) -> list[DrawCommand]:
        """TP a SL box obchodu — jediné miesto, kde ostane plán tak, ako ho engine vypočítal
        (`trades.json` má len to, čo adaptér nakoniec urobil). `x1_ms` musí byť `bar.time`,
        aby sa dal spárovať s `enter_tag` (`SPEC.sl_kind` / `tp_kind`)."""
        right = bar.time + _BOX_BARS * self.step_ms
        return [
            DrawBox(kind=kind, x1_ms=bar.time, y1=max(plan.entry, price), x2_ms=right,
                    y2=min(plan.entry, price), border_color=color, fill_color=color + "40",
                    border_width=0, obj_id=f"vop{bar.time}.{kind.value}")
            for kind, price, color in (
                (DrawKind.TP_BOX, plan.take_profit, _LONG_COLOR),
                (DrawKind.SL_BOX, plan.stop_loss, _SHORT_COLOR),
            )
        ]

    def _vwap_drawing(self, bar: Bar, vwap15: float, bias: int) -> list[DrawCommand]:
        """Úsečka VWAP od posledného bodu; farba = drift (`colUp`/`colDn`/`colFlat`).

        Bod je na **konci** baru, na ktorom sa hodnota zmenila. Nová seansa začína novú
        čiaru, s predošlým dňom sa nespája.
        """
        end_ms = bar.time + self.step_ms
        prev = self._last_point
        self._last_point = (end_ms, vwap15, self.vwap.day)
        if prev is None or prev[2] != self.vwap.day:
            return []
        color = self.cfg.colUp if bias > 0 else self.cfg.colDn if bias < 0 else self.cfg.colFlat
        return [DrawLine(VOP_VWAP, prev[0], prev[1], end_ms, vwap15, color,
                         obj_id=f"vop_vwap.{end_ms}", text="VWAP")]

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
