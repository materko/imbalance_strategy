"""MultiCharts študia — jediný súbor, ktorý sa dotýka PowerLanguage .NET API.

Cieľ je **MultiCharts .NET s Pythonom** (od verzie 15, „MultiCharts x Python").
Rozhranie je také, ako ho ukazujú vzorové študie `PY_*.Strategy.PY` v inštalácii:

* študia je **obyčajná trieda bez rodiča**; MultiCharts ju vytvorí bez argumentov
  a volá `GetInputs`/`GetInputValue`/`SetInputValue` (dialóg vstupov), potom
  `Create(ctx)`, `StartCalc()`, `CalcBar()` na každý bar, `StopCalc()` a `Destroy()`;
* všetko z grafu ide cez `ctx` (`PLStudiesProxyPython.SignalObjectPythonProxy`):
  `ctx.Bars`, `ctx.BarsOfData(2)`, `ctx.StrategyInfo.MarketPosition`, `ctx.Output`,
  `ctx.OrderCreator`, `ctx.DrwRectangle` / `DrwTrendLine` / `DrwText`;
* ordre sa vyrábajú cez `SOrderParameters` a **musia vzniknúť v `Create`** — preto
  je tu pevný pool order objektov a meno konkrétneho orderu sa dosadí až pri `Send`
  (`IOrderPriced.Send(new_name, price, numLots)`);
* beží pythonnet 3, ktorý `DateTime` **neprevádza** na Python `datetime` — čas sa
  berie z `Ticks`; farby sú `System.Drawing.Color`.

Importuje sa **až vnútri MultiCharts**; na obyčajnom Pythone `import PowerLanguage`
zlyhá, preto je `tradebot.adapters.multicharts.__init__` lazy. Testy sem siahajú
cez falošné moduly `PowerLanguage` / `System` (`test_multicharts_signal.py`).

Všetko rozhodovanie je v `runner.py` a `drawing.py` — tu je len preklad volaní.
`TradebotSignal` je generická študia; konkrétna stratégia je podtrieda so
`STRATEGY_KEY` (viď `tradebot/strategies/ibs/multicharts.py`).

### Ako to nasadiť
1. `platforms/multicharts/scripts/setup.ps1` (nainštaluje `tradebot` do Pythonu,
   ktorý MultiCharts našiel cez `where python`), potom **MultiCharts reštartovať** —
   StudyServer si Python drží od štartu a nový balík inak nevidí
2. PowerLanguage .NET Editor → **File → New → Signal**, jazyk **Python**, názov
   rovnaký ako trieda v šablóne (`IBS`)
3. Vložiť šablónu `platforms/multicharts/<Strategia>_Signal.py` — trieda so
   `PROFILE` a metódami, ktoré len delegujú sem (kompilátor bety vyžaduje `Create`
   a `CalcBar` priamo v triede študie, zdedené nevidí; stráži to
   `test_multicharts_templates.py`)
4. Na graf pridať **Data1 = graf TF** a **Data2 = informatívny TF**, ak ho stratégia
   potrebuje (IBS: `zoneDetectionTF`, 5m). Bez Data2 nevznikne ani jedna SD zóna
   a študia to zahlási v `StartCalc`.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

from tradebot.core.env import getenv

from ...core import Bar, load_profile
from ...strategies import get_spec
from .drawing import MCDrawSink
from .runner import MCRunner

__all__ = ["TradebotSignal", "PowerLanguageCanvas", "dotnet_ms", "to_dotnet_datetime", "resolution_minutes"]

#: Kam sa okrem Output okna zapisuje výpis študie (Output okno je v editore ľahké
#: prehliadnuť). Prepíše sa premennou prostredia `TRADEBOT_MC_LOG`.
DEFAULT_LOG = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "tradebot" / "multicharts.log"

#: `System.DateTime.Ticks` pre 1970-01-01 (100 ns tiky od roku 1).
_TICKS_EPOCH = 621_355_968_000_000_000

#: `_MCW_EM` z <float.h>: maska všetkých FPU výnimiek (invalid, denormal, /0, overflow,
#: underflow, inexact). Python počíta s tým, že sú maskované; MultiCharts ich po
#: spracovaní obchodu vo vlákne štúdie necháva odmaskované a prvá operácia s NaN
#: alebo podtečením potom zhodí CalcBar ako `System.ArithmeticException`.
_MCW_EM = 0x0008001F


def fpu_mask_exceptions() -> tuple[int, bool] | None:
    """Vráti (pôvodné control word, bolo_treba_maskovať) alebo None mimo Windows/MSVC."""
    try:
        import ctypes

        fn = ctypes.cdll.msvcrt._controlfp
        fn.restype = ctypes.c_uint
        fn.argtypes = [ctypes.c_uint, ctypes.c_uint]
        cw = int(fn(0, 0))
        unmasked = (cw & _MCW_EM) != _MCW_EM
        if unmasked:
            fn(_MCW_EM, _MCW_EM)
        return cw, unmasked
    except Exception:  # noqa: BLE001 - iný CRT / platforma
        return None

#: Referencie, ktoré vzorové študie pridávajú pred `from PowerLanguage import *`.
_CLR_REFERENCES = (
    "System", "System.Drawing", "PLTypes", "PLStudiesProxy", "PLStudiesProxyPython",
    "PLBuiltInFunctions", "PLTradeManager", "ATCenterProxy.interop", "PLDataLoader",
)


def _add_clr_references() -> None:  # pragma: no cover - beží len v MultiCharts
    try:
        import clr
    except ImportError:
        return
    for ref in _CLR_REFERENCES:
        try:
            clr.AddReference(ref)
        except Exception:  # noqa: BLE001 - referencia už je, alebo nie je potrebná
            pass


# --------------------------------------------------------------------------- #
# prevody .NET <-> jadro
# --------------------------------------------------------------------------- #


def dotnet_ms(value) -> int:
    """`System.DateTime` (alebo Python `datetime`) → ms epoch. Naivný čas = UTC.

    Graf musí mať Time Zone **Exchange** a burza symbolu pásmo GMT — adaptér berie
    čas baru ako UTC, tak ako Pine `time`.
    """
    ticks = getattr(value, "Ticks", None)
    if ticks is not None:
        return (int(ticks) - _TICKS_EPOCH) // 10_000
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp() * 1000)
    raise TypeError(f"neviem previesť čas {value!r}")


#: Hranice, na ktoré sa orezú x-ové súradnice kreslenia: jadro vie dať pre „extend
#: right" alebo expiráciu časy, ktoré Python `datetime` ani .NET `DateTime` nezoberú.
_MIN_DRAW_MS = int(datetime(1990, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
_MAX_DRAW_MS = int(datetime(2099, 12, 31, tzinfo=timezone.utc).timestamp() * 1000)


def to_dotnet_datetime(ms: int):
    """ms epoch → `System.DateTime` (v testoch falošný `System`). Čas sa oreže na 1990–2099."""
    from System import DateTime

    ms = min(max(int(ms), _MIN_DRAW_MS), _MAX_DRAW_MS)
    t = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return DateTime(t.year, t.month, t.day, t.hour, t.minute, t.second)


#: `EResolution` → koľko minút je jedna jednotka `Resolution.Size`.
_RESOLUTION_MINUTES = {"Minute": 1.0, "Hour": 60.0, "Second": 1 / 60, "Day": 1440.0}


def resolution_minutes(info) -> int:
    """`Bars.Info.Resolution` → minúty grafu. Iné než časové rozlíšenia adaptér nepodporuje."""
    res = info.Resolution
    kind = str(res.Type).split(".")[-1]
    factor = _RESOLUTION_MINUTES.get(kind)
    if factor is None:
        raise ValueError(f"MultiCharts rozlíšenie {kind!r} nie je časové — stratégia potrebuje minútový graf")
    minutes = int(res.Size) * factor
    if minutes != int(minutes) or minutes < 1:
        raise ValueError(f"rozlíšenie {int(res.Size)} {kind} nie je celý počet minút")
    return int(minutes)


# --------------------------------------------------------------------------- #
# kreslenie
# --------------------------------------------------------------------------- #


class PowerLanguageCanvas:
    """Plátno pre `MCDrawSink` — jediné miesto, kde sa volajú `Drw*` objekty.

    `shift_ms`: jadro dáva x-ové súradnice ako čas OTVORENIA baru (Pine), MultiCharts
    kotví objekty na čas ZATVORENIA baru — pripočíta sa preto TF grafu.
    """

    __slots__ = ("ctx", "shift_ms")

    def __init__(self, ctx, shift_ms: int = 0) -> None:
        self.ctx = ctx
        self.shift_ms = shift_ms

    def _pt(self, ms: int, price: float):
        from PowerLanguage import ChartPoint

        return ChartPoint(to_dotnet_datetime(int(ms) + self.shift_ms), float(price))

    @staticmethod
    def _color(rgb):
        from System.Drawing import Color

        r, g, b = rgb
        return Color.FromArgb(int(r), int(g), int(b))

    def create_rectangle(self, *, x1_ms, y1, x2_ms, y2, border, fill, style, width, extend_right):
        rect = self.ctx.DrwRectangle.Create(self._pt(x1_ms, y1), self._pt(x2_ms, y2))
        rect.Color = self._color(border)
        if fill is not None:
            rect.FillColor = self._color(fill)
        if width:
            rect.Size = int(width)
        return rect  # IRectangleObject nemá ExtRight — pravý okraj posúva DrawUpdate(x2_ms)

    def create_trendline(self, *, x1_ms, y1, x2_ms, y2, color, style, width):
        line = self.ctx.DrwTrendLine.Create(self._pt(x1_ms, y1), self._pt(x2_ms, y2))
        line.Color = self._color(color)
        line.Size = int(width)
        line.ExtRight = False
        return line

    def create_text(self, *, x_ms, y, text, color, above):
        obj = self.ctx.DrwText.Create(self._pt(x_ms, y), str(text))
        obj.Color = self._color(color)
        return obj

    # -- zmeny ---------------------------------------------------------- #

    def set_end_x(self, obj, ms):
        obj.End = self._pt(ms, obj.End.Price)

    def set_end_y(self, obj, price):
        from PowerLanguage import ChartPoint

        obj.End = ChartPoint(obj.End.Time, float(price))

    def set_begin_x(self, obj, ms):
        obj.Begin = self._pt(ms, obj.Begin.Price)

    def set_begin_y(self, obj, price):
        from PowerLanguage import ChartPoint

        obj.Begin = ChartPoint(obj.Begin.Time, float(price))

    def set_fill(self, obj, rgb):
        obj.FillColor = self._color(rgb)

    def set_border(self, obj, rgb):
        obj.Color = self._color(rgb)

    def set_color(self, obj, rgb):
        obj.Color = self._color(rgb)

    def delete(self, obj):
        try:
            obj.Delete()
        except Exception:  # noqa: BLE001 - objekt už graf zahodil (odstránenie študie)
            pass


# --------------------------------------------------------------------------- #
# študia
# --------------------------------------------------------------------------- #


class TradebotSignal:
    """`Create → StartCalc → CalcBar… → Destroy`, ako každá MultiCharts študia.

    Podtrieda nastaví `STRATEGY_KEY`; profil sa berie z `PROFILE` (natvrdo v šablóne),
    inak z `TRADEBOT_PROFILE`, inak default profil stratégie — až v `StartCalc`, nie
    pri importe, aby zmena prostredia platila bez reštartu.
    """

    STRATEGY_KEY: ClassVar[str] = ""
    #: Profil natvrdo (názov z tradebot/configs/<stratégia> alebo cesta); None = prostredie.
    PROFILE: ClassVar[str | None] = None
    #: Koľko vstupných limitiek na stranu môže ležať naraz. Order objekty musia
    #: vzniknúť v `Create`, takže je to pevný pool; meno sa dosadí pri `Send`.
    ENTRY_POOL: ClassVar[int] = 4
    #: Záloha za Data2: cesta k 1m Dukascopy CSV, z ktorého sa informatívny TF poskladá,
    #: keď graf druhú sériu študii nedá (beta: `BarsOfData(2)` padá). None = len Data2.
    HTF_CSV: ClassVar[str | None] = None
    #: Diagnostika: True = nekresliť nič (oddelí pády MultiCharts v kreslení od orderov).
    NO_DRAW: ClassVar[bool] = False

    def __init__(self) -> None:
        self.ctx = None
        self.runner: MCRunner | None = None
        self.sink: MCDrawSink | None = None
        self.chart_tf: int = 0
        self._informative_tfs: list[str] = []
        self._orders: dict[str, object] = {}
        #: order_id jadra -> kľúč pool slotu ("long_limit_2"), kým order žije
        self._slots: dict[str, str] = {}
        self._warned: set[str] = set()
        self._log_path = Path(os.environ.get("TRADEBOT_MC_LOG") or DEFAULT_LOG)
        self._csv_feed = None
        self._last_position = 0.0
        #: na [trade] riadky: posledný TotalTrades, ClosedEquity, posledný poslaný vstup
        self._last_closed_trades: int | None = None
        self._last_closed_equity: float = 0.0
        self._last_entry: tuple[str, float, float] | None = None  # (order_id, lots, entry)
        self._open_entry: tuple[str, float, float] | None = None
        #: počítadlá na súhrn v StopCalc — bary grafu, nakŕmené HTF bary, poslané vstupy
        self._stats = {"bars": 0, "htf": 0, "entries": 0, "exits": 0, "drawings": 0}

    # ------------------------------------------------------------------ #
    # dialóg vstupov — stratégia sa nastavuje profilom, nie vstupmi študie
    # ------------------------------------------------------------------ #

    def GetInputs(self):
        try:
            from System import Array
            from PowerLanguage import InputInfo
        except ImportError:  # pragma: no cover - mimo MultiCharts
            return []
        return Array[InputInfo]([])

    def GetInputValue(self, name):
        return None

    def SetInputValue(self, name, value):
        pass

    # ------------------------------------------------------------------ #
    # životný cyklus
    # ------------------------------------------------------------------ #

    def Create(self, ctx):
        _add_clr_references()
        self.ctx = ctx
        self._create_orders()
        # Väzba na Data2 sa skúša už tu: v bete zlyhávalo `BarsOfData(2)` volané až
        # v StartCalc/CalcBar (PriceSeriesImpl.ReBind), kým Data1 fungovala.
        self._d2_ref = None
        self._d2_create_error = None
        try:
            self._d2_ref = ctx.BarsOfData(2)
        except Exception as exc:  # noqa: BLE001
            self._d2_create_error = f"{type(exc).__name__}: {str(exc).splitlines()[0][:80]}"

    def StartCalc(self):
        self._guard_fpu("StartCalc")
        try:
            self._start_calc()
        except BaseException:  # noqa: BLE001
            self._log_exception("StartCalc")
            raise

    def _start_calc(self):
        spec = get_spec(self.STRATEGY_KEY)
        profile = self.PROFILE or getenv("PROFILE") or spec.default_profile
        cfg, inst = load_profile(profile, strategy=spec.key)
        for w in cfg.check_instrument(inst):
            self._out(f"{spec.key} config: {w}")

        self.chart_tf = resolution_minutes(self.ctx.Bars.Info)
        d2c = "OK" if getattr(self, "_d2_ref", None) is not None else f"CHYBA {getattr(self, '_d2_create_error', '?')}"
        self._out(f"{spec.key}: diagnostika serii - {self._describe_streams()}; Data2 z Create: {d2c}")
        self.runner = MCRunner(cfg, inst, self.chart_tf, spec=spec)
        self.sink = MCDrawSink(PowerLanguageCanvas(self.ctx, shift_ms=self.chart_tf * 60_000))
        self._informative_tfs = list(spec.informative_tfs(cfg)) if spec.informative_tfs else []
        # MultiCharts pri prepočte (zmena vlastností stratégie, Bar Magnifier, iný rozsah)
        # študiu nevytvára nanovo — volá len StartCalc. Všetok stav z minulého behu preč,
        # inak by napr. počítadlo obchodov z minulého behu zablokovalo [trade] riadky.
        self._slots.clear()
        self._stats = dict.fromkeys(self._stats, 0)
        self._last_position = 0.0
        self._last_closed_trades = None
        self._last_closed_equity = 0.0
        self._last_entry = None
        self._open_entry = None
        self._warned.clear()
        self._fpu_last_cw = None
        self._out(f"{spec.key}: profil {profile}, {inst.symbol}, graf {self.chart_tf}m, "
                  f"informativne TF {self._informative_tfs or '-'}, log {self._log_path}")

        self._csv_feed = None
        if self._informative_tfs and self._data2() is None:
            csv_path = self.HTF_CSV or os.environ.get("TRADEBOT_MC_HTF_CSV")
            if csv_path and Path(csv_path).exists():
                from .htf_csv import CsvHtfFeed

                htf_minutes = int(str(self._informative_tfs[0]).rstrip("m"))
                self._csv_feed = CsvHtfFeed(csv_path, htf_minutes)
                self._out(f"{spec.key}: Data2 nie je dostupna, informativny TF sa sklada z CSV - {self._csv_feed.describe()}")
            else:
                self._out(
                    f"{spec.key}: CHYBA - na grafe nie je Data2. Pridaj informativny TF "
                    f"({self._informative_tfs[0]}), alebo nastav HTF_CSV na 1m Dukascopy CSV."
                )

    def CalcBar(self):
        self._guard_fpu("CalcBar")
        try:
            self._calc_bar()
        except BaseException:  # noqa: BLE001 - aj .NET výnimky z volaní MultiCharts
            self._log_exception("CalcBar")
            raise

    def _guard_fpu(self, where: str) -> None:
        """Vráti FPU výnimky do maskovaného stavu; zmenu stavu zaloguje (raz na hodnotu)."""
        res = fpu_mask_exceptions()
        if res is None:
            return
        cw, unmasked = res
        if unmasked and cw != getattr(self, "_fpu_last_cw", None):
            self._fpu_last_cw = cw
            self._out(f"{self.STRATEGY_KEY}: FPU vynimky boli odmaskovane (control word 0x{cw:08x}) pri {where} "
                      f"na bare {self._safe_bar_time()} - maskujem, inak by NaN/podtecenie zhodilo CalcBar")

    def _log_exception(self, where: str) -> None:
        """Celý Python traceback do logu — MultiCharts z výnimky ukáže len .NET obal.

        Najprv jednoriadková hláška (typ výnimky), až potom traceback: keby formátovanie
        .NET výnimky samo zlyhalo, aspoň prvý riadok v logu ostane.
        """
        import sys
        import traceback

        exc = sys.exc_info()[1]
        self._trace(f"VYNIMKA v {where}: {type(exc).__name__}")
        bar_txt = "?"
        try:
            bar_txt = str(self.ctx.Bars.Time[0])
        except BaseException:  # noqa: BLE001
            pass
        try:
            tb = traceback.format_exc()
        except BaseException:  # noqa: BLE001
            tb = "(traceback sa nedal sformatovat)"
        self._out(f"{self.STRATEGY_KEY}: VYNIMKA v {where} na bare {bar_txt}: {type(exc).__name__}: {exc}\n{tb}")

    def _calc_bar(self):
        if self._informative_tfs:
            self._feed_htf()
        bar = self._bar(self.ctx.Bars, self.chart_tf)
        if self.runner.last_ts is None:
            # Jediné miesto, kde sa dá overiť pásmo a razenie baru bez hádania cez
            # dialógy: čo graf odovzdal Pythonu a čo z toho adaptér spravil.
            opened = datetime.fromtimestamp(bar.time / 1000, tz=timezone.utc)
            self._out(
                f"{self.STRATEGY_KEY}: prvy bar grafu Time[0]={self.ctx.Bars.Time[0]} "
                f"({self.chart_tf}m) -> otvorenie {opened:%Y-%m-%d %H:%M} UTC; "
                "ocakavane: cas zatvorenia baru v UTC (NAS100 nedela: zima 23:03 -> 23:00, leto 22:03 -> 22:00)"
            )
        position = float(self.ctx.StrategyInfo.MarketPosition)
        if position != self._last_position:
            self._trace(f"MarketPosition {self._last_position} -> {position} na bare {self.ctx.Bars.Time[0]}")
            self._last_position = position
            self._trace_strategy_state()
        busy = position != 0.0 or bool(self._slots)
        if busy:
            self._trace("krok: runner.on_bar")
        closed_trades = self._closed_trades_count()
        self._record_closed_trades(closed_trades, position)
        out = self.runner.on_bar(bar, position_size=position, closed_trades=closed_trades)
        self._stats["bars"] += 1
        self._stats["drawings"] += len(out.drawings)
        self._stats["entries"] += len(out.entries)
        if out.exit_plan is not None:
            self._stats["exits"] += 1
        if busy or out.entries:
            self._trace(f"krok: runner hotovy entries={len(out.entries)} exit_plan={out.exit_plan is not None} "
                        f"close_session={out.close_session} drawings={len(out.drawings)} cancelled={out.cancelled}")

        if not self.NO_DRAW:
            self.sink.render(out.drawings)
        self._send_entries(out)
        if out.close_session and position != 0.0:
            self._close_market(position)
        elif out.exit_plan is not None:
            self._send_exits(out.exit_plan, out.exit_stop)
        if busy or out.entries:
            self._trace("krok: bar hotovy")

    # -- voliteľné háky, ktoré MultiCharts x Python volá, ak v triede študie existujú --

    def OnOrderRejected(self, action, category, lots, price, price2):
        """MultiCharts odmietol order — bez tohto by sme sa to nedozvedeli."""
        self._out(f"{self.STRATEGY_KEY}: ORDER ODMIETNUTY action={action} category={category} "
                  f"lots={lots} price={price} price2={price2} bar={self._safe_bar_time()}")

    def OnBrokerStategyOrderFilled(self, is_buy, lots, price):
        self._trace(f"broker fill is_buy={is_buy} lots={lots} price={price}")

    def _record_closed_trades(self, closed_trades: int | None, position: float) -> None:
        """Každý nárast `TotalTrades` = uzavretý obchod → riadok `[trade] …` do logu.

        Formát číta `tester.compare.mc_log_trades`. `intrabar=1` = obchod sa otvoril aj
        zavrel v jednom bare (pozícia na close nula), vstupná cena je vtedy z plánu jadra.
        """
        if closed_trades is None:
            return
        if self._last_closed_trades is None:
            self._last_closed_trades = closed_trades
            self._last_closed_equity = self._closed_equity()
            return
        if position != 0.0 and self._open_entry is None and self._last_entry is not None:
            oid, lots, entry = self._last_entry
            try:
                entry = float(self.ctx.StrategyInfo.AvgEntryPrice) or entry
            except Exception:  # noqa: BLE001
                pass
            self._open_entry = (oid, abs(position), entry)
        if closed_trades > self._last_closed_trades:
            equity = self._closed_equity()
            pnl = equity - self._last_closed_equity
            src = self._open_entry or self._last_entry or ("?", 0.0, float("nan"))
            intrabar = self._open_entry is None
            bar_txt = self._bar_iso()
            for k in range(self._last_closed_trades + 1, closed_trades + 1):
                share = pnl if k == closed_trades else 0.0
                self._trace(f"[trade] n={k} bar={bar_txt} order={src[0]} lots={src[1]:g} entry={src[2]:.3f} "
                            f"pnl={share:.2f} intrabar={int(intrabar)}")
            self._last_closed_equity = equity
            self._last_closed_trades = closed_trades
        if position == 0.0:
            self._open_entry = None

    def _closed_equity(self) -> float:
        try:
            return float(self.ctx.StrategyInfo.ClosedEquity)
        except Exception:  # noqa: BLE001
            return 0.0

    def _bar_iso(self) -> str:
        try:
            return datetime.fromtimestamp(dotnet_ms(self.ctx.Bars.Time[0]) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        except Exception:  # noqa: BLE001
            return "?"

    def _closed_trades_count(self) -> int | None:
        """`TotalTrades` študie (uzavreté obchody); None, ak ho proxy nedá."""
        try:
            return int(self.ctx.TotalTrades)
        except Exception:  # noqa: BLE001
            return None

    def _trace_strategy_state(self) -> None:
        """Po zmene pozície prečíta equity polia po jednom — ak niektoré v MultiCharts
        padá (napr. delenie nulovou hodnotou bodu), prejaví sa to tu s menom vlastnosti."""
        for owner, names in (
            (self.ctx.StrategyInfo, ("AvgEntryPrice", "OpenEquity", "ClosedEquity")),
            (self.ctx, ("NetProfit", "GrossProfit", "GrossLoss", "TotalTrades", "MaxDrawDown")),
        ):
            for name in names:
                try:
                    self._trace(f"  {name}={getattr(owner, name)}")
                except BaseException as exc:  # noqa: BLE001
                    self._trace(f"  {name}=CHYBA {type(exc).__name__}: {str(exc).splitlines()[0][:120]}")

    def _safe_bar_time(self) -> str:
        try:
            return str(self.ctx.Bars.Time[0])
        except Exception:  # noqa: BLE001
            return "?"

    def StopCalc(self):
        last = self.runner.last_ts if self.runner is not None else None
        last_txt = datetime.fromtimestamp(last / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if last else "-"
        self._out(f"{self.STRATEGY_KEY}: koniec vypoctu - {self._stats}, posledny bar {last_txt} UTC, "
                  f"zon v evidencii {len(self.runner.engine.book) if self.runner is not None and hasattr(self.runner.engine, 'book') else '?'}")

    def Destroy(self):
        if self.sink is not None:
            self.sink.clear()

    # ------------------------------------------------------------------ #
    # bary
    # ------------------------------------------------------------------ #

    @staticmethod
    def _bar(bars, tf_minutes: int, offset: int = 0) -> Bar:
        """Bar grafu s časom OTVORENIA.

        MultiCharts razí bar časom jeho **zatvorenia** (`Time[0]` 3m baru 10:00–10:03 je
        10:03), kým `Bar.time` je ako v Pine čas otvorenia — odpočíta sa TF série.
        """
        return Bar(
            time=dotnet_ms(bars.Time[offset]) - tf_minutes * 60_000,
            open=float(bars.Open[offset]),
            high=float(bars.High[offset]),
            low=float(bars.Low[offset]),
            close=float(bars.Close[offset]),
            volume=float(bars.Volume[offset]),
        )

    def _describe_streams(self) -> str:
        """Čo študia vidí z grafu: MaxDataStream a Data1/Data2 (na hľadanie chýbajúcej Data2)."""
        parts = []
        for name in ("MaxDataStream", "StudyDataNumber", "InitialCapital", "Commission", "Slippage"):
            try:
                parts.append(f"{name}={getattr(self.ctx, name)}")
            except Exception as exc:  # noqa: BLE001
                parts.append(f"{name}=? ({type(exc).__name__})")
        try:
            info = self.ctx.Bars.Info
            parts.append(
                f"symbol BigPointValue={info.BigPointValue} PointValue={info.PointValue} PriceScale={info.PriceScale} "
                f"MinMove={info.MinMove} Category={info.Category} Currency={info.CurrencyCode} Margin={info.Margin}"
            )
        except Exception as exc:  # noqa: BLE001
            parts.append(f"symbol=? ({type(exc).__name__}: {str(exc)[:60]})")
        for n in (1, 2):
            try:
                b = self.ctx.BarsOfData(n)
                info = b.Info
                parts.append(f"Data{n}={info.Name} {int(info.Resolution.Size)} {str(info.Resolution.Type).split('.')[-1]} bars={int(b.CurrentBar)}")
            except Exception as exc:  # noqa: BLE001
                parts.append(f"Data{n}=CHYBA {type(exc).__name__}: {str(exc).splitlines()[0][:80]}")
        return "; ".join(parts)

    def _data2(self):
        """Data2 alebo None, ak na grafe nie je (proxy vtedy vyhodí výnimku).

        `MaxDataStream` sa zámerne nepoužíva — v MultiCharts x Python beta vracia 1 aj
        pri dvoch sériách na grafe. Dôvod výnimky sa raz vypíše, aby sa dal odlíšiť
        chýbajúci Data2 od chyby adaptéra.
        """
        if getattr(self, "_d2_ref", None) is not None:
            return self._d2_ref
        try:
            d2 = self.ctx.BarsOfData(2)
        except Exception as exc:  # noqa: BLE001
            if "data2" not in self._warned:
                self._warned.add("data2")
                self._out(f"{self.STRATEGY_KEY}: BarsOfData(2) zlyhalo: {type(exc).__name__}: {exc}")
            return None
        return d2

    def _feed_htf(self):
        """Data2 = informatívny TF stratégie. Berie sa až **uzavretý** bar, teda offset [1].

        Bez Data2 sa kŕmi z CSV (`HTF_CSV`) všetkými barmi zavretými do zatvorenia
        aktuálneho baru grafu.
        """
        if self._csv_feed is not None:
            close_ms = dotnet_ms(self.ctx.Bars.Time[0])
            self._stats["htf"] += self._csv_feed.feed_until(self.runner, close_ms)
            return
        d2 = self._data2()
        if d2 is None or int(d2.CurrentBar) < 2:
            return
        self.runner.feed_htf(self._bar(d2, resolution_minutes(d2.Info), offset=1))
        self._stats["htf"] += 1

    # ------------------------------------------------------------------ #
    # ordre
    # ------------------------------------------------------------------ #

    def _create_orders(self):
        """Všetky order objekty naraz — po `Create` už `OrderCreator` nové nevyrobí."""
        from PowerLanguage import Contracts, EOrderAction, OrderExit, SOrderParameters

        oc = self.ctx.OrderCreator
        P = SOrderParameters
        orders: dict[str, object] = {}
        for i in range(self.ENTRY_POOL):
            orders[f"long_limit_{i}"] = oc.Limit(P(Contracts.UserSpecified, f"tb_long_{i}", EOrderAction.Buy))
            orders[f"short_limit_{i}"] = oc.Limit(P(Contracts.UserSpecified, f"tb_short_{i}", EOrderAction.SellShort))
        orders["long_market_0"] = oc.MarketNextBar(P(Contracts.UserSpecified, "tb_long_mkt", EOrderAction.Buy))
        orders["short_market_0"] = oc.MarketNextBar(P(Contracts.UserSpecified, "tb_short_mkt", EOrderAction.SellShort))
        for side, action in (("long", EOrderAction.Sell), ("short", EOrderAction.BuyToCover)):
            orders[f"sl_{side}"] = oc.Stop(P(Contracts.Default, "tb_sl", action, OrderExit.FromAll))
            orders[f"tp_{side}"] = oc.Limit(P(Contracts.Default, "tb_tp", action, OrderExit.FromAll))
            # Pine `strategy.close(immediately=true)` = close AKTUALNEHO baru -> MarketThisBar;
            # MarketNextBar by na konci piatkovej seansy zavrel az na nedelnom otvoreni.
            orders[f"end_{side}"] = oc.MarketThisBar(P(Contracts.Default, "tb_session_end", action, OrderExit.FromAll))
        self._orders = orders

    def _slot_for(self, live) -> str | None:
        """Pool slot pre živý order; None, ak je pool plný (nahlási sa raz)."""
        key = self._slots.get(live.order_id)
        if key is not None:
            return key
        side = "long" if live.is_long else "short"
        kind = "market" if live.market else "limit"
        used = set(self._slots.values())
        n = 1 if live.market else self.ENTRY_POOL
        for i in range(n):
            candidate = f"{side}_{kind}_{i}"
            if candidate not in used:
                self._slots[live.order_id] = candidate
                return candidate
        if f"pool:{side}_{kind}" not in self._warned:
            self._warned.add(f"pool:{side}_{kind}")
            self._out(f"{self.STRATEGY_KEY}: viac nez {n} zivych {side} {kind} orderov naraz - {live.order_id} sa neposle (zvys ENTRY_POOL)")
        return None

    @staticmethod
    def _lots(qty: float) -> int:
        """Celé loty pre .NET `Int32`; NaN/inf/obrovské qty sa orežú, nie zhodia študiu."""
        try:
            lots = int(round(float(qty)))
        except (OverflowError, ValueError):
            return 1
        return max(1, min(lots, 1_000_000))

    def _send_entries(self, out):
        """Ordre sa posielajú ZNOVA každý bar — v MultiCharts platia len jeden bar.

        Spolu so vstupom idú aj jeho SL/TP: v Pine `strategy.exit` platí od momentu
        vyplnenia, MultiCharts by inak prvé výstupné ordre dostal až o bar neskôr a
        obchod zavretý vnútri vstupného baru by minul. Exit ordre bez pozície
        MultiCharts ignoruje, takže je to bezpečné.
        """
        live_ids = {live.order_id for live in out.entries}
        for stale in [k for k in self._slots if k not in live_ids]:
            del self._slots[stale]
        pre_exit: dict[str, object] = {}
        for live in out.entries:
            pre_exit["long" if live.is_long else "short"] = live.plan
            key = self._slot_for(live)
            if key is None:
                continue
            order = self._orders[key]
            lots = self._lots(live.plan.qty)
            self._last_entry = (live.order_id, float(lots), float(live.plan.entry))
            if live.market:
                self._trace(f"Send market {key} name={live.order_id} lots={lots}")
                order.Send(live.order_id, lots)
            else:
                self._trace(f"Send limit {key} name={live.order_id} price={float(live.plan.entry)} lots={lots}")
                order.Send(live.order_id, float(live.plan.entry), lots)
            self._trace("Send OK")
        if out.exit_plan is None:
            for plan in pre_exit.values():
                self._send_exits(plan)

    def _close_market(self, position: float):
        """Pine `strategy.close(immediately=true)` na konci poslednej seansy dňa.

        Strana sa berie zo znamienka pozície, nie z plánu — plán môže byť v tom bare
        už zrušený (engine posiela CANCEL spolu s CLOSE).
        """
        side = "long" if position > 0 else "short"
        self._trace(f"Send end_{side}")
        self._orders[f"end_{side}"].Send()

    def _send_exits(self, plan, stop_price=None):
        """SL a TP tiež musia ísť každý bar, kým je pozícia otvorená.

        `stop_price` je SL po trailingu; bez neho platí pôvodný z plánu.
        """
        side = "long" if plan.direction.value == 1 else "short"
        sl = float(plan.stop_loss if stop_price is None else stop_price)
        self._trace(f"Send sl_{side} {sl} / tp_{side} {float(plan.take_profit)}")
        self._orders[f"sl_{side}"].Send(sl)
        self._orders[f"tp_{side}"].Send(float(plan.take_profit))

    # ------------------------------------------------------------------ #

    def _trace(self, text: str) -> None:
        """Riadok len do súboru (ordre, kreslenie) — na hľadanie miesta, kde MultiCharts padne."""
        try:
            with open(self._log_path, "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now():%H:%M:%S} [trace] {text}" + chr(10))
        except OSError:  # pragma: no cover
            pass

    def _out(self, text: str) -> None:
        """Výpis do súboru (vždy, ako prvé) a do Output okna (`IOutput.WriteLine(format, args)`).

        Súbor ide prvý: keby WriteLine na dlhom texte zlyhal, traceback by sa stratil.
        Zložené zátvorky sú pre WriteLine formátovacie, treba ich zdvojiť.
        """
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_path, "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {text}\n")
        except OSError:  # pragma: no cover - log je len pomôcka
            pass
        msg = str(text).replace("{", "{{").replace("}", "}}")
        try:
            self.ctx.Output.WriteLine(msg)
        except TypeError:  # pragma: no cover - závisí od verzie pythonnet
            try:
                from System import Array, Object

                self.ctx.Output.WriteLine(msg, Array[Object]([]))
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001 - Output okno nesmie zhodiť študiu
            pass


def __getattr__(name: str):
    """Spätná kompatibilita: `IBSSignal` žije v `tradebot.strategies.ibs.multicharts`."""
    if name == "IBSSignal":
        from tradebot.strategies.ibs.multicharts import IBSSignal

        return IBSSignal
    raise AttributeError(name)
