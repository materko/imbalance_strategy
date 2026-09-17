"""Engine SD Zones: zóna vzniká tam, odkiaľ cena impulzívne odišla z krátkej konsolidácie.

Priebeh:

  1. **báza** — 1 až ``baseMaxBars`` sviečok s malými telami (``baseMaxBodyPct``),
     ktorých celý rozsah je užší než ``baseMaxWidthAtr``
  2. **impulz** — prvá sviečka odchodu (leg-out) hneď za bázou s telom aspoň
     ``impulseMinBodyAtr`` a podielom tela aspoň ``impulseMinBodyPct``
  3. **odchod** — do ``legOutMaxBars`` barov (počítajúc impulz) musí niektorý bar **zavrieť**
     za hranou bázy v smere odchodu aspoň o ``legOutMinAtr`` (ATR z baru pred impulzom).
     Odchod môže byť rozložený do viacerých sviečok; keď sa nestihne, alebo cena medzitým
     zavrie späť za druhou hranou bázy, kandidát zanikne. ``legOutMinAtr = 0`` krok vypne
     (zóna vzniká hneď na impulze, ako pred 2026-09-17).
  4. **formácia** sa klasifikuje podľa smeru príchodu a odchodu: Rally-Base-Rally,
     Drop-Base-Drop (pokračovacie), Drop-Base-Rally, Rally-Base-Drop (obratové)
  5. **zóna** vzniká na bare, ktorý odchod dokončil (nie skôr — žiadny pohľad dopredu),
     obchodovateľná je od nasledujúceho baru; ``pfz`` je úzka (telo bázy), ``wfz`` široká
     (knôt po knôt). Keď sa cena počas odchodu vrátila k zóne, zóna už nie je čerstvá.
  6. **návrat** — pri prvom návrate do čerstvej zóny sa vstupuje; zóna sa tým minie
  7. **SL** za vzdialenejšiu hranu zóny, **TP** podľa ``tpMode``

Pravidlo odchodu je podľa verejných supply/demand skriptov na TradingView: odchod = **záver**
za bázou o násobok ATR (nie knôt), zóna sa kreslí až na bare, ktorý odchod uzavrel, a pohyb
smie dobehnúť cez niekoľko „follow-through" sviečok. Zdroje a zdôvodnenie sú
v ``docs/ANALYTIKA.md`` stratégie.

Engine je čistý: žiadne I/O, žiadny globálny stav, všetko je v ``self``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawLabel, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.warmup import Warmup
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan, TrailingPlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType

from .config import EntryMode, SDZoneConfig, SlMode, TpMode, ZoneMode
from .drawing import SD_BASE, SD_DEMAND, SD_ENTRY, SD_PATTERN, SD_SUPPLY

__all__ = ["SDZoneEngine"]

_DEMAND_FILL = "#10b98122"
_SUPPLY_FILL = "#ef444422"
_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"


@dataclass
class _Zone:
    """Jedna supply/demand zóna."""

    direction: Direction          # LONG = demand (kupuje sa z nej), SHORT = supply
    top: float                    # horná hranica
    bottom: float                 # dolná hranica
    born_bar: int
    born_ms: int
    pattern: str                  # "RBR" | "DBD" | "DBR" | "RBD"
    continuation: bool
    fresh: bool = True
    used: bool = False

    @property
    def proximal(self) -> float:
        """Hrana, ktorou cena do zóny vstupuje (pri demande horná, pri supply dolná)."""
        return self.top if self.direction is Direction.LONG else self.bottom

    @property
    def distal(self) -> float:
        """Vzdialenejšia hrana — za ňu ide stop."""
        return self.bottom if self.direction is Direction.LONG else self.top

    @property
    def height(self) -> float:
        return self.top - self.bottom


@dataclass
class _Candidate:
    """Báza s impulzom, ktorej odchod ešte nie je dokončený — zatiaľ nie je zónou."""

    zone: _Zone                   # born_bar sa doplní na bare, ktorý odchod dokončí
    start_bar: int                # index impulznej sviečky (prvý bar odchodu)
    target: float                 # záver, ktorý treba prekonať (hrana bázy ± legOutMinAtr)
    base_high: float              # knôt po knôt — z nich sa meria odchod aj návrat
    base_low: float

class SDZoneEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: SDZoneConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000

        # okno histórie musí pokryť ATR, trendový priemer aj bázu s odchodom
        window = max(int(cfg.atrLen), int(cfg.trendMaLen) if cfg.useTrendFilter else 0) \
            + int(cfg.baseMaxBars) + int(cfg.legOutMaxBars) + 8
        self.history = BarHistory(maxlen=window + 32, atr_len=int(cfg.atrLen))
        #: predhistória grafu = to okno (životnosť zón a denný limit sa do nej nepočítajú)
        self.warmup = Warmup(self.chart_tf_minutes).add("ATR/SMA trendu + baza + odchod", window)
        self.required_history = self.warmup.chart_bars

        self._zone = ZoneInfo(cfg.tradeTZ)
        self._zones: list[_Zone] = []
        self._pending: tuple[str, int] | None = None
        self._entry_bar = -1
        self._day: tuple[int, int, int] | None = None
        self._trades_today = 0
        self._in_window_prev = False
        #: bázy s impulzom, ktoré čakajú na dokončenie odchodu (ešte nie sú zónou)
        self._candidates: list[_Candidate] = []

    # ------------------------------------------------------------------ #
    # pomocné
    # ------------------------------------------------------------------ #

    @staticmethod
    def _body_pct(bar: Bar) -> float:
        span = bar.high - bar.low
        if span <= 0:
            return 0.0
        return abs(bar.close - bar.open) / span * 100.0

    def _in_window(self, bar: Bar) -> bool:
        cfg = self.cfg
        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return False
        if not cfg.useTradeWindow:
            return True
        minutes = local.hour * 60 + local.minute
        return cfg.window_start_minutes <= minutes < cfg.window_end_minutes

    def _trend_ok(self, direction: Direction) -> bool:
        cfg = self.cfg
        if not cfg.useTrendFilter:
            return True
        n = int(cfg.trendMaLen)
        if not self.history.has(n):
            return False
        ma = sum(self.history[i].close for i in range(n)) / n
        cena = self.history[0].close
        return cena > ma if direction is Direction.LONG else cena < ma

    # ------------------------------------------------------------------ #
    # detekcia zóny
    # ------------------------------------------------------------------ #

    def _detect(self, idx: int, atr: float, atr_prev: float) -> _Candidate | None:
        """Hľadá bázu + impulz končiaci na poslednom uzavretom bare.

        Vráti kandidáta, nie zónu: zónou sa stane až v `_advance`, keď cena od bázy naozaj
        odíde. `atr_prev` je ATR baru pred impulzom — cieľ odchodu sa z neho počíta preto,
        aby veľký rozsah samotného impulzu nezdvihol latku, ktorú má prekonať
        (tak to robí aj Zone Forge [AFD] na TradingView).
        """
        cfg = self.cfg
        if atr <= 0:
            return None
        impulz = self.history[0]
        telo = abs(impulz.close - impulz.open)
        min_telo = cfg.impulseMinBodyAtr.resolve(self.inst, price=impulz.close, atr=atr)
        if telo < min_telo or self._body_pct(impulz) < cfg.impulseMinBodyPct:
            return None
        hore = impulz.close > impulz.open

        max_sirka = cfg.baseMaxWidthAtr.resolve(self.inst, price=impulz.close, atr=atr)
        # Skúšaj bázy od NAJDLHŠEJ po najkratšiu. Metodika kreslí zónu z celej konsolidácie,
        # nie z poslednej sviečky pred impulzom — a pri hľadaní od najkratšej by sa vždy
        # trafila tá jednosviečková a `baseMaxBars` by nerobil nič.
        for n in range(int(cfg.baseMaxBars), 0, -1):
            if not self.history.has(n + 2):
                break
            baza = [self.history[i] for i in range(1, n + 1)]
            if any(self._body_pct(b) > cfg.baseMaxBodyPct for b in baza):
                continue
            top = max(b.high for b in baza)
            bot = min(b.low for b in baza)
            if top - bot > max_sirka or top <= bot:
                continue

            prichod = self.history[n + 1]
            prichod_hore = prichod.close > prichod.open
            continuation = (prichod_hore == hore)
            if not cfg.trades_pattern(continuation):
                continue

            direction = Direction.LONG if hore else Direction.SHORT
            if direction is Direction.LONG and not cfg.allow_long:
                continue
            if direction is Direction.SHORT and not cfg.allow_short:
                continue

            base_high, base_low = top, bot
            if cfg.zoneMode is ZoneMode.PFZ:
                # úzka zóna: len telá sviečok bázy
                top = max(max(b.open, b.close) for b in baza)
                bot = min(min(b.open, b.close) for b in baza)
                if top <= bot:
                    return None

            pat = ("RBR" if (prichod_hore and hore) else "DBR" if hore else
                   "DBD" if not prichod_hore else "RBD")
            zona = _Zone(direction=direction, top=top, bottom=bot, born_bar=idx,
                         born_ms=baza[-1].time, pattern=pat, continuation=continuation)
            # odchod sa meria od hrany bázy knôt po knôt, nezávisle od zoneMode — šírka
            # kreslenej zóny nesmie meniť, ktoré zóny vôbec vzniknú
            odchod = cfg.legOutMinAtr.resolve(self.inst, price=impulz.close,
                                              atr=atr_prev if atr_prev > 0 else atr)
            target = base_high + odchod if hore else base_low - odchod
            return _Candidate(zone=zona, start_bar=idx, target=target,
                              base_high=base_high, base_low=base_low)
        return None

    def _advance(self, bar: Bar, idx: int) -> list[_Zone]:
        """Posunie čakajúcich kandidátov o bar; vráti zóny, ktorých odchod sa práve dokončil.

        Pravidlá (pre demand, supply zrkadlovo):
          * odchod je dokončený, keď bar **zavrie** nad ``target`` — knôt nestačí
          * musí sa to stať do ``legOutMaxBars`` barov vrátane impulzu, inak kandidát zanikne
          * záver pod spodnou hranou bázy kandidáta zruší (formácia sa nepotvrdila)
          * keď sa cena po impulze dotkla zóny skôr, než odchod dobehol, zóna vznikne,
            ale nie je čerstvá — prvý návrat už prebehol
        """
        cfg = self.cfg
        max_bars = max(1, int(cfg.legOutMaxBars))
        hotove: list[_Zone] = []
        cakaju: list[_Candidate] = []
        for c in self._candidates:
            z = c.zone
            long = z.direction is Direction.LONG
            if idx > c.start_bar and (bar.low <= z.top if long else bar.high >= z.bottom):
                z.fresh = False
            if (bar.close >= c.target) if long else (bar.close <= c.target):
                z.born_bar = idx
                hotove.append(z)
                continue
            if (bar.close < c.base_low) if long else (bar.close > c.base_high):
                continue
            if idx - c.start_bar + 1 >= max_bars:
                continue
            cakaju.append(c)
        self._candidates = cakaju
        return hotove

    # ------------------------------------------------------------------ #
    # plán obchodu
    # ------------------------------------------------------------------ #

    def _plan(self, z: _Zone, entry: float, atr: float) -> TradePlan | None:
        cfg = self.cfg
        long = z.direction is Direction.LONG
        buffer = cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr)
        if cfg.slMode is SlMode.ZONE:
            stop = z.distal - buffer if long else z.distal + buffer
        else:
            dist = cfg.slAtrMult.resolve(self.inst, price=entry, atr=atr)
            stop = entry - dist if long else entry + dist

        sl_distance = abs(entry - stop)
        if sl_distance < self.inst.tick_size * 2:
            return None
        min_sl = cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr)
        if min_sl > 0 and sl_distance < min_sl:
            return None

        if cfg.tpMode is TpMode.ATR:
            dist = cfg.tpAtrMult.resolve(self.inst, price=entry, atr=atr)
        elif cfg.tpMode is TpMode.OPPOSITE:
            dist = self._opposite_distance(z, entry) or sl_distance * cfg.rrRatio
        else:
            dist = sl_distance * cfg.rrRatio
        take = entry + dist if long else entry - dist

        qty = (cfg.position_qty(self.inst, cfg.riskDollar, sl_distance)
               if cfg.riskDollar > 0 else 1.0)
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)

        trailing = None
        if cfg.enableTrailing:
            act = sl_distance * cfg.trailActivationR
            off = sl_distance * cfg.trailOffsetR
            tick = self.inst.tick_size or 1.0
            trailing = TrailingPlan(activation_price_distance=act, offset_price_distance=off,
                                    activation_ticks=act / tick, offset_ticks=off / tick)
        return TradePlan(direction=z.direction, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop),
                         take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl_distance, trailing=trailing)

    def _opposite_distance(self, z: _Zone, entry: float) -> float | None:
        """Vzdialenosť k najbližšej opačnej čerstvej zóne, ak nejaká pred cenou je."""
        long = z.direction is Direction.LONG
        kand = [o for o in self._zones
                if o.direction is not z.direction and not o.used
                and ((o.bottom > entry) if long else (o.top < entry))]
        if not kand:
            return None
        ciel = min(o.bottom for o in kand) if long else max(o.top for o in kand)
        d = abs(ciel - entry)
        return d if d > 0 else None

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg

        atr_prev = self.history.atr
        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index

        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        day = (local.year, local.month, local.day)
        if day != self._day:
            self._day = day
            self._trades_today = 0

        if self._pending is not None and ctx.position_size == 0.0 and idx - self._pending[1] >= 2:
            out.orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], self._pending[1],
                                          reason="nevyplnené"))
            self._pending = None
        if ctx.position_size != 0.0:
            self._pending = None
        elif self._entry_bar >= 0 and idx > self._entry_bar:
            self._entry_bar = -1

        in_window = self._in_window(bar)
        if cfg.closeAtWindowEnd and self._in_window_prev and not in_window and ctx.position_size != 0.0:
            out.close_session = True
            for oid in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx,
                                              reason="koniec obchodného okna"))
        self._in_window_prev = in_window

        if (cfg.maxHoldBars > 0 and ctx.position_size != 0.0 and self._entry_bar >= 0
                and idx - self._entry_bar >= cfg.maxHoldBars):
            for oid in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx,
                                              reason=f"drží sa dlhšie než {cfg.maxHoldBars} barov"))
            self._entry_bar = -1

        # ---- 1.-5. vznik novej zóny --------------------------------------- #
        kand = self._detect(idx, atr, atr_prev)
        nove: list[_Zone] = []
        if kand is not None and not any(
                z.born_ms == kand.zone.born_ms and z.direction is kand.zone.direction
                for z in [*self._zones, *(c.zone for c in self._candidates)]):
            if cfg.legOutMinAtr.value > 0:
                self._candidates.append(kand)
            else:
                nove.append(kand.zone)       # odchod sa nemeria — zóna hneď na impulze
        if self._candidates:
            nove.extend(self._advance(bar, idx))
        for nova in nove:
            self._zones.append(nova)
            if len(self._zones) > cfg.maxZones:
                self._zones = self._zones[-int(cfg.maxZones):]
            if cfg.showZones:
                koniec = bar.time + self.step_ms * int(cfg.maxZoneAgeBars)
                out.drawings.append(DrawBox(
                    SD_DEMAND if nova.direction is Direction.LONG else SD_SUPPLY,
                    nova.born_ms, nova.top, koniec, nova.bottom,
                    _DEMAND_FILL if nova.direction is Direction.LONG else _SUPPLY_FILL,
                    obj_id=f"sd.{nova.born_ms}.{nova.pattern}",
                    text=f"{nova.pattern} {'demand' if nova.direction is Direction.LONG else 'supply'}",
                ))
            if cfg.showPatterns:
                long = nova.direction is Direction.LONG
                out.drawings.append(DrawLabel(
                    SD_PATTERN, bar.time, bar.low if long else bar.high, nova.pattern,
                    "#ffffff", style=LabelStyle.NONE, above=not long,
                    bg_color=_LONG_COLOR if long else _SHORT_COLOR,
                    # na jednom bare môže dobehnúť odchod viacerých zón
                    obj_id=f"sdp.{bar.time}.{nova.born_ms}"))

        # ---- starnutie a zneplatnenie zón --------------------------------- #
        ziju: list[_Zone] = []
        for z in self._zones:
            if z.used or idx - z.born_bar > cfg.maxZoneAgeBars:
                continue
            # cena zónu prerazila naskrz -> zanikla
            if (z.direction is Direction.LONG and bar.close < z.bottom) or \
               (z.direction is Direction.SHORT and bar.close > z.top):
                continue
            ziju.append(z)
        self._zones = ziju

        if ctx.position_size != 0.0 or self._pending is not None:
            return out
        if not in_window or self._trades_today >= cfg.maxTradesPerDay:
            return out

        # ---- 5. návrat do zóny -------------------------------------------- #
        for z in self._zones:
            if z.used or z.born_bar == idx:
                continue
            long = z.direction is Direction.LONG
            dotyk = bar.low <= z.top if long else bar.high >= z.bottom
            if not dotyk:
                continue
            if cfg.requireFresh and not z.fresh:
                continue
            if not self._trend_ok(z.direction):
                z.fresh = False          # zónu sme videli, ale filter ju nepustil
                continue

            hlbka = z.height * (cfg.entryDepthPct / 100.0)
            cena_limit = z.proximal - hlbka if long else z.proximal + hlbka

            if cfg.entryMode is EntryMode.LIMIT:
                entry, typ = cena_limit, OrderType.LIMIT
            elif cfg.entryMode is EntryMode.CLOSE:
                vnutri = z.bottom <= bar.close <= z.top
                if not vnutri:
                    continue
                entry, typ = bar.close, OrderType.MARKET
            else:  # REJECT — sviečka sa zóny dotkla, ale zavrela mimo nej v smere obchodu
                odmietla = bar.close > z.top if long else bar.close < z.bottom
                if not odmietla:
                    continue
                entry, typ = bar.close, OrderType.MARKET

            plan = self._plan(z, entry, atr)
            z.fresh = False
            if plan is None:
                continue
            z.used = True
            oid = f"sd:{idx}"
            out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=z.direction,
                                          plan=plan, order_type=typ,
                                          reason=f"návrat do zóny {z.pattern}"))
            self._pending = (oid, idx)
            self._entry_bar = idx
            self._trades_today += 1
            out.drawings.append(DrawLabel(
                SD_ENTRY, bar.time, bar.low if long else bar.high,
                f"{'LONG' if long else 'SHORT'} {z.pattern}", "#ffffff",
                style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                bg_color=_LONG_COLOR if long else _SHORT_COLOR,
                obj_id=f"sde.{bar.time}"))
            break
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
