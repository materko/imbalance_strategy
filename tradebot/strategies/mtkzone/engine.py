"""Engine MTK ZONE — SD zóny z vyšších TF a vstupy limit na zónu / IBS / pin bar na grafe.

Predloha je Pine „VP SD ZÓNY 50 — stratégia“ (10. 11. 2026). Na každom uzavretom bare grafu:

1. **Zóny** — bary grafu sa skladajú na TF zón (`zoneTf1`, voliteľne `zoneTf2`) rovnakým pravidlom ako
   `tradebot/core/candles.py` (`TimeframeAggregator`). Na každej uzavretej sviečke TF zón sa hľadá:
   * **klasická SD / vrchol profilu** — odchod na predošlej sviečke TF zón (telo ≥ `impMult` × ATR), pred ním
     základňa 1–`baseMax` malých sviečok (telo ≤ `baseBodyMax` × ATR); dopyt = od tela základne po jej low;
   * **nárast objemu** — práve uzavretá sviečka má objem ≥ `volSpike` × priemer objemu pred ňou a telo
     ≥ `impMultVol` × ATR; späť na začiatok pohybu (najviac 3 väčšie sviečky tým istým smerom), zóna = tichá
     základňa pred ním (malé telo alebo objem pod priemerom, inak posledná sviečka pred pohybom);
   * **potvrdenia** — SD vzor, vrchol volume profilu (POC / PEAK posledných `lookback` sviečok TF zón) v zóne,
     nárast objemu; zóna vznikne len pri ≥ `minConf` potvrdeniach a kvalite ≥ `minScore`;
   * voliteľne zóna priamo na POC / najväčšom PEAK (`usePocZone`, 1 potvrdenie, každých `pocEvery` sviečok).
   Prekrytie s aktívnou zónou toho istého TF a smeru → ostane lepšia (zóna z objemu má prednosť); najviac
   `maxZones` aktívnych na stranu a TF, pri plnom ustúpi zóna najďalej od ceny.
2. **Test** — prvý dotyk zóny (dopyt: low ≤ horná hrana) zónu zareže; ďalej ju sledujú len modely IBS a pin bar.
3. **Modely** na otestovaných zónach (`modelBars` sviečok od dotyku):
   * IBS presne podľa `tradebot/strategies/ibs/statemachine.py`: gap proti smeru zóny → výstup zo zóny
     (`st1Max`) → potvrdenie zatvorením za telom imbalance sviečky (`st2ConfTicks`, `st2Max`) → retest jej
     otvorenia (`st3Max`) → limit na otvorenie (`st5Max` sviečok), SL za swingom `ibsSlLookback` sviečok;
   * pin bar v zóne v smere (rozsah ≥ `pbMinRange`, knôt ≥ `pbRatio` × telo, telo ≤ `pbBodyPos` % od okraja),
     vstup marketom, SL za knôtom.
4. **Vstup** (len bez pozície): pin bar → IBS → limit na bližšiu hranu najbližšej neotestovanej zóny (SL za
   zónou). Filtre: VWAP (pri limite cena vstupu voči VWAP), seansa NY, odstup od posledného výstupu, vek a
   kvalita zóny, max. riziko a vzdialenosť. Cieľ = `rrRatio` × riziko. Každá zóna dá najviac jeden obchod.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawDelete, DrawLabel, DrawLine, DrawUpdate, LineStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from ..ibsentry.fvg import TimeframeAggregator
from .config import MtkZoneConfig, VwapAnchor, VwapMode
from .drawing import MZ_CB, MZ_IFVG, MZ_RETEST, MZ_ZONE

__all__ = ["MtkZoneEngine"]

NY = ZoneInfo("America/New_York")
DEM_COLOR, SUP_COLOR, VOL_COLOR = "#1de9b6", "#ff5252", "#000000"


# ---------------------------------------------------------------------------- #
# vyšší TF zón: uzavreté sviečky, ATR (Pine ta.atr = RMA), priemer objemu
# ---------------------------------------------------------------------------- #

class _HtfSeries:
    def __init__(self, minutes: int, atr_len: int, vol_len: int, keep: int) -> None:
        self.minutes = minutes
        self.agg = TimeframeAggregator(minutes)
        self.atr_len, self.vol_len = atr_len, vol_len
        self.bars: deque[Bar] = deque(maxlen=keep)
        self.atr: deque[float | None] = deque(maxlen=keep)
        self.vsma: deque[float | None] = deque(maxlen=keep)
        self.count = 0
        self._atr: float | None = None
        self._trs: list[float] = []
        self._vols: deque[float] = deque(maxlen=vol_len)

    def push(self, chart_bar: Bar) -> Bar | None:
        closed = self.agg.push(chart_bar)
        if closed is None:
            return None
        prev = self.bars[-1] if self.bars else None
        tr = closed.high - closed.low if prev is None else max(closed.high - closed.low, abs(closed.high - prev.close),
                                                               abs(closed.low - prev.close))
        if self._atr is None:
            self._trs.append(tr)
            if len(self._trs) >= self.atr_len:
                self._atr = sum(self._trs[-self.atr_len:]) / self.atr_len
        else:
            self._atr = (self._atr * (self.atr_len - 1) + tr) / self.atr_len
        self._vols.append(closed.volume)
        self.bars.append(closed)
        self.atr.append(self._atr)
        self.vsma.append(sum(self._vols) / self.vol_len if len(self._vols) >= self.vol_len else None)
        self.count += 1
        return closed

    def has(self, k: int) -> bool:
        return len(self.bars) > k

    def b(self, k: int) -> Bar:
        return self.bars[-1 - k]

    def a(self, k: int) -> float | None:
        return self.atr[-1 - k]

    def v(self, k: int) -> float | None:
        return self.vsma[-1 - k]


@dataclass
class _Profile:
    tot: list[float]
    total: float
    lo: float
    step: float
    poc: int


def _profile(bars: list[Bar], rows: int) -> _Profile | None:
    """Volume profil (Pine f_profile): objem sviečky do riadkov podľa prekrytia rozsahu, bez rozdelenia na nákup / predaj."""
    if not bars:
        return None
    hi = max(b.high for b in bars)
    lo = min(b.low for b in bars)
    step = (hi - lo) / rows
    if step <= 0:
        return None
    tot = [0.0] * rows
    for b in bars:
        rng = b.high - b.low
        v = b.volume or 0.0
        if rng <= 0:
            r0 = min(rows - 1, max(0, int((b.low - lo) // step)))
            tot[r0] += v
            continue
        ra = max(0, int((b.low - lo) // step))
        rb = min(rows - 1, int((b.high - lo) // step))
        for r in range(ra, rb + 1):
            rl = lo + r * step
            sh = max(0.0, min(b.high, rl + step) - max(b.low, rl)) / rng
            if sh > 0:
                tot[r] += v * sh
    total = sum(tot)
    poc = max(range(rows), key=lambda r: tot[r])
    return _Profile(tot, total, lo, step, poc)


def _peaks(p: _Profile, rows: int, peak_min: float) -> list[bool]:
    out = [False] * rows
    for r in range(rows):
        t = p.tot[r]
        pct = 100 * t / p.total if p.total > 0 else 0.0
        if r == p.poc or (pct >= peak_min and (r == 0 or t >= p.tot[r - 1]) and (r == rows - 1 or t > p.tot[r + 1])):
            out[r] = True
    return out


def _peak_in(p: _Profile | None, rows: int, peak_min: float, top: float, bot: float) -> float:
    """Najväčší vrchol profilu (podiel objemu), ktorého stred leží v zóne (± pol riadka); 0 = žiadny."""
    if p is None or p.total <= 0:
        return 0.0
    pk = 0.0
    for r, is_pk in enumerate(_peaks(p, rows, peak_min)):
        mid = p.lo + (r + 0.5) * p.step
        if is_pk and bot - 0.5 * p.step <= mid <= top + 0.5 * p.step:
            pk = max(pk, p.tot[r] / p.total)
    return pk


@dataclass
class _Cand:
    top: float
    bot: float
    dir: int
    score: float
    pk: float
    rv: float
    src: str
    left_ms: int


@dataclass
class _Zone:
    uid: int
    top: float
    bot: float
    dir: int
    score: float
    pk: float
    rv: float
    src: str
    tf: int
    left_ms: int
    born: int
    active: bool = True
    touch_idx: int | None = None
    used: bool = False
    dead: bool = False
    ist: int = 0
    ist_idx: int = 0
    imb_open: float = 0.0
    imb_bt: float = 0.0
    imb_bb: float = 0.0
    imb_ms: int = 0
    pin_now: bool = False
    box_id: str = ""
    ibox_id: str = ""

    @property
    def mid(self) -> float:
        return (self.top + self.bot) / 2

    @property
    def is_vol(self) -> bool:
        return "OBJEM" in self.src


# ---------------------------------------------------------------------------- #
# VWAP s kotvou (deň CME / otvorenie NY 9:30 / týždeň / mesiac) — Pine ta.vwap(hlc3, anchor)
# ---------------------------------------------------------------------------- #

class _AnchoredVwap:
    def __init__(self, anchor: VwapAnchor) -> None:
        self.anchor = anchor
        self.key: tuple | None = None
        self.pv = 0.0
        self.vol = 0.0
        self.value: float | None = None

    def _key(self, t_ms: int) -> tuple:
        local = datetime.fromtimestamp(t_ms / 1000, tz=NY)
        if self.anchor is VwapAnchor.NY:
            d = (local - timedelta(hours=9, minutes=30)).date()
            return (d.year, d.month, d.day)
        cme = (local + timedelta(hours=6)).date()          # obchodný deň CME začína 18:00 New York
        if self.anchor is VwapAnchor.WEEK:
            y, w, _ = cme.isocalendar()
            return (y, w)
        if self.anchor is VwapAnchor.MONTH:
            return (cme.year, cme.month)
        return (cme.year, cme.month, cme.day)

    def push(self, bar: Bar) -> None:
        k = self._key(bar.time)
        if k != self.key:
            self.key, self.pv, self.vol = k, 0.0, 0.0
        v = bar.volume or 0.0
        self.pv += (bar.high + bar.low + bar.close) / 3 * v
        self.vol += v
        self.value = self.pv / self.vol if self.vol > 0 else self.value


class MtkZoneEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: MtkZoneConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg, self.inst = cfg, inst
        self.tf = max(1, int(chart_tf_minutes))
        keep = int(cfg.lookback) + int(cfg.baseMax) + 12
        self.slots: list[_HtfSeries] = []
        for use, m in ((cfg.useZ1, cfg.zoneTf1), (cfg.useZ2, cfg.zoneTf2)):
            if use and all(s.minutes != int(m) for s in self.slots):
                self.slots.append(_HtfSeries(max(int(m), self.tf), int(cfg.atrLen), int(cfg.volLen), keep))
        self.warmup = Warmup(self.tf)
        for s in self.slots:
            self.warmup.add(f"zóny {s.minutes}m ({cfg.lookback} sviečok)", keep, s.minutes)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=max(64, int(cfg.imbLookback) + 4, int(cfg.ibsSlLookback) + 2),
                                  atr_len=int(cfg.atrLen))
        self.vwap = _AnchoredVwap(VwapAnchor(cfg.vwapAnchor))
        self.zones: list[_Zone] = []
        self._uid = 0
        #: čakajúce limity: druh (L / S / LI / SI) -> (order_id, vstup, SL, zóna)
        self.pending: dict[str, tuple[str, float, float, _Zone]] = {}
        self._was_in_pos = False
        self._last_exit: int | None = None

    # ------------------------------------------------------------------ #
    # zóny
    # ------------------------------------------------------------------ #

    def _detect(self, s: _HtfSeries) -> list[_Cand]:
        cfg, out = self.cfg, []
        rows, pmin = int(cfg.rows), float(cfg.peakMin)
        prof: _Profile | None = None

        def profile() -> _Profile | None:
            nonlocal prof
            if prof is None and s.has(0):
                n = min(int(cfg.lookback), len(s.bars))
                prof = _profile([s.b(k) for k in range(n)], rows)
            return prof

        # --- klasická SD / vrchol profilu: odchod na [1], základňa [2..] ---
        if (cfg.useClassic or cfg.usePeak) and s.has(2 + 1):
            a = s.a(1)
            d1 = s.b(1)
            body = abs(d1.close - d1.open)
            if a and a > 0 and body >= cfg.impMult * a:
                dr = 1 if d1.close > d1.open else -1
                k, top, bot = 0, None, None
                for b in range(2, 2 + int(cfg.baseMax)):
                    if not s.has(b):
                        break
                    x = s.b(b)
                    if abs(x.close - x.open) <= cfg.baseBodyMax * (s.a(b) or a):
                        k += 1
                        if dr == 1:
                            top = max(x.open, x.close) if top is None else max(top, x.open, x.close)
                            bot = x.low if bot is None else min(bot, x.low)
                        else:
                            top = x.high if top is None else max(top, x.high)
                            bot = min(x.open, x.close) if bot is None else min(bot, x.open, x.close)
                    else:
                        break
                if k > 0 and top > bot and (d1.close > top if dr == 1 else d1.close < bot):
                    pk = _peak_in(profile(), rows, pmin, top, bot)
                    v2 = s.v(2) if s.has(2) else None
                    rv = d1.volume / v2 if v2 else 1.0
                    peak_ok = cfg.usePeak and pk > 0
                    conf = 1 + (1 if peak_ok else 0) + (1 if cfg.useVolSurge and rv >= cfg.volSpike else 0)
                    if (cfg.useClassic or peak_ok) and conf >= cfg.minConf:
                        bs = min(1.0, body / a / (2 * cfg.impMult))
                        pks = min(1.0, pk / (2 * pmin / 100)) if peak_ok else 0.0
                        score = 35 * bs + 30 * min(1.0, rv / 2.0) + 35 * max(pks, bs if cfg.useClassic else 0.0)
                        if score >= cfg.minScore:
                            out.append(_Cand(top, bot, dr, score, pk if peak_ok else 0.0, rv,
                                             "PROFIL" if peak_ok else "SD", s.b(1 + k).time))

        # --- nárast objemu: sviečka [0] s dobrým objemom → začiatok pohybu → tichá základňa ---
        if cfg.useVolSurge and s.has(2):
            a0, b0, v1 = s.a(0), s.b(0), s.v(1)
            body0 = abs(b0.close - b0.open)
            if a0 and a0 > 0 and v1 and b0.volume >= cfg.volSpike * v1 and body0 >= cfg.impMultVol * a0:
                dr = 1 if b0.close > b0.open else -1
                j = 1
                while j <= 3 and s.has(j):
                    x = s.b(j)
                    same = x.close > x.open if dr == 1 else x.close < x.open
                    if same and abs(x.close - x.open) > cfg.baseBodyMax * (s.a(j) or a0):
                        j += 1
                    else:
                        break
                k, top, bot = 0, None, None
                for b in range(j, j + int(cfg.baseMax)):
                    if not s.has(b):
                        break
                    x = s.b(b)
                    small = abs(x.close - x.open) <= cfg.baseBodyMax * (s.a(b) or a0)
                    vb = s.v(b + 1) if s.has(b + 1) else None
                    quiet = bool(vb) and x.volume <= vb
                    if small or quiet or (k == 0 and b == j):
                        k += 1
                        if dr == 1:
                            top = max(x.open, x.close) if top is None else max(top, x.open, x.close)
                            bot = x.low if bot is None else min(bot, x.low)
                        else:
                            top = x.high if top is None else max(top, x.high)
                            bot = min(x.open, x.close) if bot is None else min(bot, x.open, x.close)
                        if not (small or quiet):
                            break
                    else:
                        break
                if k > 0 and top > bot and (b0.close > top if dr == 1 else b0.close < bot):
                    rv = b0.volume / v1
                    pk = _peak_in(profile(), rows, pmin, top, bot) if cfg.usePeak else 0.0
                    score = (35 * min(1.0, body0 / a0 / (2 * cfg.impMultVol)) + 30 * min(1.0, rv / 2.0)
                             + 35 * min(1.0, rv / (2 * cfg.volSpike)))
                    conf = 1 + (1 if pk > 0 else 0) + (1 if cfg.useClassic and body0 >= cfg.impMult * a0 else 0)
                    if score >= cfg.minScore and conf >= cfg.minConf:
                        out.append(_Cand(top, bot, dr, score, pk, rv, "OBJEM+PROFIL" if pk > 0 else "OBJEM",
                                         s.b(j + k - 1).time))

        # --- POC a najväčší ďalší PEAK (každých pocEvery sviečok TF zón) ---
        if cfg.usePocZone and cfg.minConf <= 1 and s.count % int(cfg.pocEvery) == 0 and s.count > cfg.lookback:
            p = profile()
            if p is not None and p.total > 0:
                pk = _peaks(p, rows, pmin)
                best = -1
                for r in range(rows):
                    if pk[r] and r != p.poc and abs(r - p.poc) > 1 and (best < 0 or p.tot[r] > p.tot[best]):
                        best = r
                for r, name in ((p.poc, "POC"), (best, "PEAK")):
                    if r < 0:
                        continue
                    bot = p.lo + r * p.step
                    top = bot + p.step
                    pct = p.tot[r] / p.total
                    out.append(_Cand(top, bot, 0, min(100.0, 100.0 * pct / (4 * pmin / 100)), pct, 0.0, name,
                                     s.b(0).time))
        return out

    def _text(self, z: _Zone) -> str:
        t = f"{'DOPYT' if z.dir == 1 else 'PONUKA'} {z.score:.0f} · {z.tf}m {z.src}"
        if z.pk > 0:
            t += f" · PEAK {100 * z.pk:.1f}% VOL"
        if z.rv > 0:
            t += f" · OBJEM {z.rv:.1f}×"
        return t + ("" if z.active else " · otestovaná")

    def _remove(self, z: _Zone, out: EngineOutput) -> None:
        self.zones.remove(z)
        if z.box_id and self.cfg.showZones:
            out.drawings.append(DrawDelete(z.box_id))

    def _add_zone(self, c: _Cand, tf: int, bar: Bar, idx: int, out: EngineOutput) -> None:
        cfg = self.cfg
        dr = c.dir
        if dr == 0:                               # POC / PEAK: smer podľa ceny, cena v zóne → nič
            if c.top < bar.close:
                dr = 1
            elif c.bot > bar.close:
                dr = -1
            else:
                return
            if c.score < cfg.minScore:
                return
        is_vol = "OBJEM" in c.src
        for o in [z for z in self.zones if z.active and z.dir == dr and z.tf == tf and c.top > z.bot and c.bot < z.top]:
            if (o.score >= c.score and not (is_vol and not o.is_vol)) or (o.is_vol and not is_vol):
                return
            self._remove(o, out)
        act = [z for z in self.zones if z.active and z.dir == dr and z.tf == tf]
        if len(act) >= cfg.maxZones:
            self._remove(max(act, key=lambda z: abs(z.mid - bar.close)), out)
        self._uid += 1
        z = _Zone(self._uid, c.top, c.bot, dr, c.score, c.pk, c.rv, c.src, tf, c.left_ms, idx - 1)
        z.box_id = f"mz.{z.uid}"
        self.zones.append(z)
        if cfg.showZones:
            col = VOL_COLOR if is_vol else (DEM_COLOR if dr == 1 else SUP_COLOR)
            out.drawings.append(DrawBox(MZ_ZONE, min(c.left_ms, bar.time), c.top, bar.time, c.bot, col, col + "40",
                                        extend_right=True, obj_id=z.box_id, zone_uid=z.uid, text=self._text(z)))

    # ------------------------------------------------------------------ #
    # IBS gap (tradebot/strategies/ibs/ta/imbalance.py)
    # ------------------------------------------------------------------ #

    def _find_imb(self, z: _Zone, idx: int, atr: float):
        cfg, h = self.cfg, self.history
        min_imb = cfg.minImbSize.resolve(self.inst, price=h[0].close, atr=atr)
        max_d = cfg.imbMaxDistTicks * self.inst.tick_size
        best = None
        for lb in range(int(cfg.imbLookback)):
            if not h.has(lb + 2) or idx - (lb + 2) < z.born:
                continue
            near, mid, far = h[lb], h[lb + 1], h[lb + 2]
            bull = near.low > far.high and mid.close > far.high and near.low - far.high >= min_imb
            bear = near.high < far.low and mid.close < far.low and far.low - near.high >= min_imb
            d = None
            through = mid.high >= z.top and mid.low <= z.bot
            if z.dir == 1 and bear and (mid.open > z.top or through):
                d = max(0.0, mid.low - z.top)
            if z.dir == -1 and bull and (mid.open < z.bot or through):
                d = max(0.0, z.bot - mid.high)
            if d is not None and d <= max_d and (best is None or d < best[0]):
                gt = far.low if z.dir == 1 else near.low
                gb = near.high if z.dir == 1 else far.high
                best = (d, mid.open, max(mid.open, mid.close), min(mid.open, mid.close), far.time, gt, gb)
        return best

    def _models(self, bar: Bar, idx: int, atr: float, out: EngineOutput) -> None:
        cfg, tick = self.cfg, self.inst.tick_size
        draw = cfg.showIbsDraw
        for z in self.zones:
            z.pin_now = False
            if z.active or z.used or z.dead or z.touch_idx is None:
                continue
            long = z.dir == 1
            age = idx - z.touch_idx
            in_zone = bar.high >= z.bot and bar.low <= z.top
            broken = bar.low < z.bot if long else bar.high > z.top
            if cfg.usePin and z.ist == 0 and in_zone:
                rng = bar.high - bar.low
                btop, bbot = max(bar.open, bar.close), min(bar.open, bar.close)
                blen = btop - bbot
                wick_ok = (blen <= 0 or bbot - bar.low >= blen * cfg.pbRatio) if long else \
                    (blen <= 0 or bar.high - btop >= blen * cfg.pbRatio)
                pos_ok = (bar.high - btop <= rng * cfg.pbBodyPos / 100) if long else \
                    (bbot - bar.low <= rng * cfg.pbBodyPos / 100)
                min_rng = cfg.pbMinRange.resolve(self.inst, price=bar.close, atr=atr)
                z.pin_now = rng >= min_rng and wick_ok and pos_ok
            if cfg.useIBS:
                if z.ist == 0:
                    hit = self._find_imb(z, idx, atr)
                    if hit is not None:
                        _, z.imb_open, z.imb_bt, z.imb_bb, gl_ms, gt, gb = hit
                        z.ist, z.ist_idx, z.imb_ms = 1, idx, self.history[1].time
                        z.ibox_id = f"mz.i.{z.uid}"
                        if draw:
                            out.drawings.append(DrawBox(MZ_IFVG, gl_ms, max(gt, gb), bar.time, min(gt, gb), "#c026d3",
                                                        "#f472b64d", obj_id=z.ibox_id, zone_uid=z.uid, text="iFVG"))
                elif z.ist == 1:
                    if idx - z.ist_idx > cfg.st1Max:
                        self._ibs_fail(z, bar, out)
                    elif (bar.high > z.top and bar.low <= z.top) if long else (bar.low < z.bot and bar.high >= z.bot):
                        z.ist, z.ist_idx = 2, idx
                elif z.ist == 2:
                    if idx - z.ist_idx > cfg.st2Max:
                        self._ibs_fail(z, bar, out)
                    elif (bar.close > z.imb_bt + cfg.st2ConfTicks * tick) if long else \
                            (bar.close < z.imb_bb - cfg.st2ConfTicks * tick):
                        z.ist, z.ist_idx = 3, idx
                        if draw:
                            cb = z.imb_bt if long else z.imb_bb
                            out.drawings.append(DrawLine(MZ_CB, z.imb_ms, cb, bar.time, cb, "#94a3b8",
                                                         obj_id=f"mz.cb.{z.uid}", zone_uid=z.uid, text="CB"))
                            out.drawings.append(DrawUpdate(z.ibox_id, "x2_ms", bar.time))
                elif z.ist == 3:
                    if idx - z.ist_idx > cfg.st3Max:
                        self._ibs_fail(z, bar, out)
                    elif (bar.low <= z.imb_open) if long else (bar.high >= z.imb_open):
                        z.ist, z.ist_idx = 4, idx
                        if draw:
                            out.drawings.append(DrawLabel(MZ_RETEST, bar.time, z.imb_open, "●", "#2962ff",
                                                          obj_id=f"mz.r.{z.uid}", zone_uid=z.uid))
                            out.drawings.append(DrawUpdate(z.ibox_id, "x2_ms", bar.time))
                elif z.ist == 4 and idx - z.ist_idx >= cfg.st5Max:
                    z.dead = True
            if z.ist == 0 and not z.pin_now and (broken or age > cfg.modelBars):
                z.dead = True

    def _ibs_fail(self, z: _Zone, bar: Bar, out: EngineOutput) -> None:
        z.dead = True
        if self.cfg.showIbsDraw and z.ibox_id:
            out.drawings.append(DrawUpdate(z.ibox_id, "x2_ms", bar.time))
            out.drawings.append(DrawUpdate(z.ibox_id, "fill_color", "#94a3b826"))

    # ------------------------------------------------------------------ #
    # vstupy
    # ------------------------------------------------------------------ #

    def _plan(self, long: bool, entry: float, sl: float) -> TradePlan | None:
        cfg = self.cfg
        risk = entry - sl if long else sl - entry
        if risk < self.inst.tick_size * 2:
            return None
        if cfg.maxRiskTicks > 0 and risk > cfg.maxRiskTicks * self.inst.tick_size:
            return None
        tp = entry + cfg.rrRatio * risk if long else entry - cfg.rrRatio * risk
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, risk)
        return TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(sl), take_profit=self.inst.round_price(tp),
                         qty=qty if qty > 0 else 1.0, sl_distance=risk)

    def _vwap_ok(self, long: bool, price: float) -> bool:
        mode = VwapMode(self.cfg.vwapMode)
        if mode is VwapMode.OFF:
            return True
        v = self.vwap.value
        if v is None:
            return False
        above = price > v
        below = price < v
        if mode is VwapMode.WITH:
            return above if long else below
        return below if long else above

    def _in_sess(self, bar: Bar) -> bool:
        if not self.cfg.useSess:
            return True
        local = datetime.fromtimestamp(bar.time / 1000, tz=NY)
        hm = local.hour * 100 + local.minute
        a, b = int(self.cfg.sessStart), int(self.cfg.sessEnd)
        return a <= hm < b if a <= b else (hm >= a or hm < b)

    def _zone_ok(self, z: _Zone, idx: int) -> bool:
        cfg = self.cfg
        return z.score >= cfg.minEntryScore and (cfg.maxZoneAge == 0 or idx - z.born <= cfg.maxZoneAge)

    def _cancel_all(self, out: EngineOutput, idx: int, reason: str) -> None:
        for kind, (oid, _, _, _) in list(self.pending.items()):
            out.orders.append(OrderIntent(OrderAction.CANCEL, oid, idx, reason=reason))
        self.pending.clear()

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        cfg, out = self.cfg, EngineOutput()
        self.history.append(bar)
        idx = self.history.bar_index
        atr = self.history.atr
        self.vwap.push(bar)

        # 1. nové zóny z uzavretých sviečok TF zón
        for s in self.slots:
            if s.push(bar) is not None:
                for c in self._detect(s):
                    self._add_zone(c, s.minutes, bar, idx, out)
        # 2. test: prvý dotyk zónu zareže
        for z in self.zones:
            if z.active and idx > z.born and (bar.low <= z.top if z.dir == 1 else bar.high >= z.bot):
                z.active, z.touch_idx = False, idx
                if cfg.showZones:
                    out.drawings.append(DrawUpdate(z.box_id, "extend_right", False))
                    out.drawings.append(DrawUpdate(z.box_id, "x2_ms", bar.time))
                    out.drawings.append(DrawUpdate(z.box_id, "border_style", LineStyle.DASHED))
                    out.drawings.append(DrawUpdate(z.box_id, "text", self._text(z)))
        # 3. modely IBS a pin bar na otestovaných zónach
        self._models(bar, idx, atr, out)
        # dokončené zóny preč (kresba ostáva)
        self.zones = [z for z in self.zones if z.active or not (z.used or z.dead)]

        # 4. pozícia: vyplnený order → jeho zóna je použitá, ostatné čakajúce preč (OCO)
        for oid in ctx.dropped_entry_ids:
            for kind in [k for k, v in self.pending.items() if v[0] == oid]:
                del self.pending[kind]
        in_pos = ctx.position_size != 0.0
        if in_pos:
            if not self._was_in_pos:
                for kind, (oid, _, _, z) in self.pending.items():
                    if oid in ctx.open_order_ids:
                        z.used = True
            self._cancel_all(out, idx, "pozícia otvorená (OCO)")
        elif self._was_in_pos:
            self._last_exit = idx
        self._was_in_pos = in_pos
        if in_pos:
            return out

        gap_ok = (self._last_exit is None or idx - self._last_exit >= cfg.minGap) and self._in_sess(bar)
        buf = cfg.slBufTicks * self.inst.tick_size
        dz = sz = di = si = dp = sp = None
        for z in self.zones:
            if z.active and self._zone_ok(z, idx):
                if z.dir == 1 and z.top < bar.close and (dz is None or z.top > dz.top):
                    dz = z
                if z.dir == -1 and z.bot > bar.close and (sz is None or z.bot < sz.bot):
                    sz = z
            if not z.active and not z.used and not z.dead and z.score >= cfg.minEntryScore:
                if z.ist == 4:
                    if z.dir == 1 and (di is None or z.ist_idx > di.ist_idx):
                        di = z
                    if z.dir == -1 and (si is None or z.ist_idx > si.ist_idx):
                        si = z
                if z.pin_now:
                    if z.dir == 1:
                        dp = z
                    else:
                        sp = z

        # pin bar má prednosť (market), potom IBS, potom limit na zónu
        for z, long in ((dp, True), (sp, False)):
            if z is None or not cfg.usePin or not gap_ok:
                continue
            if (long and not cfg.allow_long) or (not long and not cfg.allow_short) or not self._vwap_ok(long, bar.close):
                continue
            sl = bar.low - buf if long else bar.high + buf
            plan = self._plan(long, bar.close, sl)
            if plan is None:
                continue
            self._cancel_all(out, idx, "pin bar")
            z.used = True
            out.orders.append(OrderIntent(OrderAction.ENTRY, f"mz:P:{idx}", z.uid, direction=plan.direction,
                                          plan=plan, order_type=OrderType.MARKET,
                                          reason=f"MTK ZONE pin bar {z.tf}m {z.src}"))
            return out

        sw = [self.history[k] for k in range(min(int(cfg.ibsSlLookback), len(self.history)))]
        want: dict[str, tuple[_Zone, bool, float, float]] = {}
        if cfg.useIBS and di is not None and cfg.allow_long:
            want["LI"] = (di, True, di.imb_open, min(b.low for b in sw) - buf)
        if cfg.useIBS and si is not None and cfg.allow_short:
            want["SI"] = (si, False, si.imb_open, max(b.high for b in sw) + buf)
        if cfg.useLimit and dz is not None and cfg.allow_long:
            want["L"] = (dz, True, dz.top, dz.bot - buf)
        if cfg.useLimit and sz is not None and cfg.allow_short:
            want["S"] = (sz, False, sz.bot, sz.top + buf)
        for kind in ("LI", "SI", "L", "S"):
            plan = None
            if kind in want and gap_ok:
                z, long, e, sl = want[kind]
                if self._vwap_ok(long, e) and (cfg.maxDist == 0 or abs(bar.close - e) <= cfg.maxDist):
                    plan = self._plan(long, e, sl)
            cur = self.pending.get(kind)
            if plan is None:
                if cur is not None:
                    out.orders.append(OrderIntent(OrderAction.CANCEL, cur[0], idx, reason="podmienka vstupu neplatí"))
                    del self.pending[kind]
                continue
            z = want[kind][0]
            if cur is not None and cur[1] == plan.entry and cur[2] == plan.stop_loss and cur[3] is z:
                continue
            if cur is not None:
                out.orders.append(OrderIntent(OrderAction.CANCEL, cur[0], idx, reason="nová cena limitu"))
            oid = f"mz:{kind}:{idx}"
            self.pending[kind] = (oid, plan.entry, plan.stop_loss, z)
            out.orders.append(OrderIntent(OrderAction.ENTRY, oid, z.uid, direction=plan.direction, plan=plan,
                                          order_type=OrderType.LIMIT,
                                          reason=f"MTK ZONE {'IBS' if 'I' in kind else 'limit na zónu'} {z.tf}m {z.src}"))
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
