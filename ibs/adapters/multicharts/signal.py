"""MultiCharts študia — jediný súbor, ktorý sa dotýka PowerLanguage .NET API.

Importuje sa **až vnútri MultiCharts**; na obyčajnom Pythone `import PowerLanguage`
zlyhá, preto je `ibs.adapters.multicharts.__init__` lazy a testy sem nesiahajú.

Všetko rozhodovanie je v `runner.py` a `drawing.py` — tu je len preklad volaní.

### Ako to nasadiť
1. `platforms/multicharts/scripts/setup.ps1` (nainštaluje `ibs` do globálneho Pythonu)
2. PowerLanguage .NET Editor → **File → New → Signal**, jazyk **Python.NET**
3. Do súboru dať::

       from ibs.adapters.multicharts.signal import IBSSignal as _IBSSignal

       class IBS(_IBSSignal):
           pass

4. Na graf pridať **Data1 = graf TF** (3m) a **Data2 = detekčný TF** (`zoneDetectionTF`, 5m).
   Bez Data2 nevznikne ani jedna SD zóna a študia to zahlási v `StartCalc`.
"""

from __future__ import annotations

import os

from ...core import Bar, load_profile
from .drawing import MCDrawSink
from .runner import MCRunner

__all__ = ["IBSSignal", "PowerLanguageCanvas"]

try:  # pragma: no cover - beží len v MultiCharts
    from PowerLanguage import SignalObject
except ImportError:  # pragma: no cover
    SignalObject = object


class PowerLanguageCanvas:
    """Plátno pre `MCDrawSink` — jediné miesto, kde sa volajú `Drw*` objekty."""

    __slots__ = ("sig",)

    def __init__(self, sig) -> None:
        self.sig = sig

    @staticmethod
    def _dt(ms: int):
        from datetime import datetime, timezone

        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(tzinfo=None)

    def create_rectangle(self, *, x1_ms, y1, x2_ms, y2, border, fill, style, width, extend_right):
        from PowerLanguage import ChartPoint

        rect = self.sig.DrwRectangle.Create(
            ChartPoint(self._dt(x1_ms), y1), ChartPoint(self._dt(x2_ms), y2)
        )
        rect.Color = border
        if fill is not None:
            rect.FillColor = fill
        rect.ExtRight = extend_right
        return rect

    def create_trendline(self, *, x1_ms, y1, x2_ms, y2, color, style, width):
        from PowerLanguage import ChartPoint

        line = self.sig.DrwTrendLine.Create(
            ChartPoint(self._dt(x1_ms), y1), ChartPoint(self._dt(x2_ms), y2)
        )
        line.Color = color
        line.Size = width
        return line

    def create_text(self, *, x_ms, y, text, color, above):
        from PowerLanguage import ChartPoint

        obj = self.sig.DrwText.Create(ChartPoint(self._dt(x_ms), y), text)
        obj.Color = color
        return obj

    # -- zmeny ---------------------------------------------------------- #

    def set_end_x(self, obj, ms):
        from PowerLanguage import ChartPoint

        obj.End = ChartPoint(self._dt(ms), obj.End.Price)

    def set_end_y(self, obj, price):
        from PowerLanguage import ChartPoint

        obj.End = ChartPoint(obj.End.Time, price)

    def set_begin_x(self, obj, ms):
        from PowerLanguage import ChartPoint

        obj.Begin = ChartPoint(self._dt(ms), obj.Begin.Price)

    def set_begin_y(self, obj, price):
        from PowerLanguage import ChartPoint

        obj.Begin = ChartPoint(obj.Begin.Time, price)

    def set_fill(self, obj, rgb):
        obj.FillColor = rgb

    def set_border(self, obj, rgb):
        obj.Color = rgb

    def set_color(self, obj, rgb):
        obj.Color = rgb

    def delete(self, obj):
        obj.Delete()


class IBSSignal(SignalObject):
    """`Create → StartCalc → CalcBar → Destroy`, ako každá MultiCharts študia."""

    #: Profil sa berie z premennej prostredia, aby sa nemusel meniť kód študie.
    PROFILE = os.environ.get("IBS_PROFILE", "mnq_3m")

    def __init__(self, ctx):  # pragma: no cover - beží len v MultiCharts
        super().__init__(ctx)
        self.runner: MCRunner | None = None
        self.sink: MCDrawSink | None = None
        self._entries: dict[str, object] = {}

    # ------------------------------------------------------------------ #

    def StartCalc(self):  # pragma: no cover - beží len v MultiCharts
        cfg, inst = load_profile(self.PROFILE)
        warnings = cfg.check_instrument(inst)
        for w in warnings:
            self.Output.WriteLine(f"IBS config: {w}")

        chart_tf = int(self.Bars.Info.Resolution.Size)
        self.runner = MCRunner(cfg, inst, chart_tf)
        self.sink = MCDrawSink(PowerLanguageCanvas(self))

        if self.BarsOfData(2) is None:
            self.Output.WriteLine(
                "IBS: CHYBA - na grafe nie je Data2. Pridaj detekcny TF "
                f"({cfg.zoneDetectionTF}m), inak nevznikne ani jedna SD zona."
            )

    def CalcBar(self):  # pragma: no cover - beží len v MultiCharts
        self._feed_htf()
        bar = self._bar(self.Bars)
        out = self.runner.on_bar(bar, position_size=float(self.StrategyInfo.MarketPosition))

        self.sink.render(out.drawings)
        self._send_entries(out)
        if out.exit_plan is not None:
            self._send_exits(out.exit_plan)

    def Destroy(self):  # pragma: no cover - beží len v MultiCharts
        if self.sink is not None:
            self.sink.clear()

    # ------------------------------------------------------------------ #

    @staticmethod
    def _bar(bars) -> Bar:  # pragma: no cover - beží len v MultiCharts
        from datetime import timezone

        t = bars.Time[0].replace(tzinfo=timezone.utc)
        return Bar(
            time=int(t.timestamp() * 1000),
            open=float(bars.Open[0]),
            high=float(bars.High[0]),
            low=float(bars.Low[0]),
            close=float(bars.Close[0]),
            volume=float(bars.Volume[0]),
        )

    def _feed_htf(self):  # pragma: no cover - beží len v MultiCharts
        """Data2 = detekčný TF. Berie sa až **uzavretý** bar, teda offset [1]."""
        d2 = self.BarsOfData(2)
        if d2 is None or d2.CurrentBar < 2:
            return
        from datetime import timezone

        t = d2.Time[1].replace(tzinfo=timezone.utc)
        self.runner.feed_htf(
            Bar(
                time=int(t.timestamp() * 1000),
                open=float(d2.Open[1]),
                high=float(d2.High[1]),
                low=float(d2.Low[1]),
                close=float(d2.Close[1]),
                volume=float(d2.Volume[1]),
            )
        )

    def _send_entries(self, out):  # pragma: no cover - beží len v MultiCharts
        """Ordre sa posielajú ZNOVA každý bar — v MultiCharts platia len jeden bar."""
        from PowerLanguage import EOrderAction, OrderCategory, SignalType

        for live in out.entries:
            key = live.order_id
            order = self._entries.get(key)
            if order is None:
                action = EOrderAction.Buy if live.is_long else EOrderAction.SellShort
                maker = self.OrderCreator.MarketNextBar if live.market else self.OrderCreator.Limit
                order = maker(SignalType.UserSpecified, OrderCategory.Enter, action, key)
                self._entries[key] = order
            if live.market:
                order.Send(live.plan.qty)
            else:
                order.Send(live.plan.entry, live.plan.qty)

    def _send_exits(self, plan):  # pragma: no cover - beží len v MultiCharts
        """SL a TP tiež musia ísť každý bar, kým je pozícia otvorená."""
        from PowerLanguage import EOrderAction, OrderCategory, SignalType

        long = plan.direction.value == 1
        action = EOrderAction.Sell if long else EOrderAction.BuyToCover
        stop = self._entries.get("__sl")
        if stop is None:
            stop = self.OrderCreator.Stop(
                SignalType.UserSpecified, OrderCategory.Exit, action, "ibs_sl"
            )
            self._entries["__sl"] = stop
        target = self._entries.get("__tp")
        if target is None:
            target = self.OrderCreator.Limit(
                SignalType.UserSpecified, OrderCategory.Exit, action, "ibs_tp"
            )
            self._entries["__tp"] = target
        stop.Send(plan.stop_loss)
        target.Send(plan.take_profit)
