"""`TradebotSignal` proti falošnému MultiCharts x Python rozhraniu.

`PowerLanguage` a `System` existujú len vnútri MultiCharts; tu sa podstrčia falošné
moduly s presne tými menami a podpismi, ktoré ukázala reflexia knižníc bety
(`SOrderParameters`, `Contracts`, `OrderExit`, `IOrderPriced.Send(new_name, price, lots)`,
`ChartPoint(DateTime, price)`, `Color.FromArgb`). Testuje sa preklad volaní: pool
orderov, mená pri Send, čas baru z `Ticks`, Data2, kreslenie, Output.
"""

from __future__ import annotations

import sys
import types
from datetime import datetime, timezone

import pytest

from tradebot.adapters.multicharts.runner import BarOutput, LiveOrder
from tradebot.core import DrawBox, DrawKind, IBSConfig
from tradebot.core.drawing import DrawUpdate
from tradebot.core.risk import TradePlan
from tradebot.core.types import MNQ, Direction

MIN = 60_000
T0 = 1_736_121_600_000  # 2025-01-06 00:00 UTC
TICKS_EPOCH = 621_355_968_000_000_000


# --------------------------------------------------------------------------- #
# falošný .NET
# --------------------------------------------------------------------------- #


class FakeDateTime:
    """`System.DateTime`: len Ticks, ako ho vidí pythonnet 3 (bez prevodu na datetime)."""

    def __init__(self, y, mo, d, h=0, mi=0, s=0):
        t = datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc)
        self.Ticks = int(t.timestamp() * 1000) * 10_000 + TICKS_EPOCH

    @classmethod
    def from_ms(cls, ms: int) -> "FakeDateTime":
        t = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        return cls(t.year, t.month, t.day, t.hour, t.minute, t.second)

    @property
    def ms(self) -> int:
        return (self.Ticks - TICKS_EPOCH) // 10_000

    def __repr__(self) -> str:
        return f"DateTime({datetime.fromtimestamp(self.ms / 1000, tz=timezone.utc):%Y-%m-%d %H:%M})"


class FakeArray:
    def __class_getitem__(cls, item):
        return lambda items: list(items)


class FakeColor:
    @staticmethod
    def FromArgb(r, g, b):
        return ("rgb", r, g, b)


class ChartPoint:
    def __init__(self, time, price):
        self.Time, self.Price = time, price


class SOrderParameters:
    def __init__(self, lots, name, action, exit_info=None):
        self.Lots, self.Name, self.Action, self.ExitTypeInfo = lots, name, action, exit_info


class Contracts:
    Default = "Default"
    UserSpecified = "UserSpecified"


class OrderExit:
    FromAll = "FromAll"


class EOrderAction:
    Buy, Sell, SellShort, BuyToCover = "Buy", "Sell", "SellShort", "BuyToCover"


class EResolution:
    Minute, Hour = "EResolution.Minute", "EResolution.Hour"


class InputInfo:
    pass


class FakeOrder:
    def __init__(self, kind, params):
        self.kind, self.params, self.sent = kind, params, []

    def Send(self, *args):
        self.sent.append(args)


class FakeOrderCreator:
    def __init__(self):
        self.created: list[FakeOrder] = []

    def _make(self, kind, params):
        o = FakeOrder(kind, params)
        self.created.append(o)
        return o

    def Limit(self, p):
        return self._make("limit", p)

    def Stop(self, p):
        return self._make("stop", p)

    def MarketNextBar(self, p):
        return self._make("market", p)

    def MarketThisBar(self, p):
        return self._make("market_this_bar", p)


class FakeDrawObj:
    def __init__(self, kind, *args):
        self.kind, self.args, self.deleted = kind, args, False
        self.Begin = args[0] if args else None
        self.End = args[1] if len(args) > 1 else None

    def Delete(self):
        self.deleted = True
        return True


class FakeDrwFactory:
    def __init__(self, kind):
        self.kind, self.objects = kind, []

    def Create(self, *args):
        o = FakeDrawObj(self.kind, *args)
        self.objects.append(o)
        return o


class Series:
    """`Bars.Close[0]` = posledný, `[1]` = predchádzajúci."""

    def __init__(self, values):
        self.values = list(values)

    def __getitem__(self, bars_ago):
        return self.values[-1 - bars_ago]


class FakeBars:
    def __init__(self, tf_minutes, bars, res_type="EResolution.Minute", size=None):
        self.Info = types.SimpleNamespace(
            Name="NAS100",
            Resolution=types.SimpleNamespace(Type=res_type, Size=size if size is not None else tf_minutes),
        )
        self.set(bars)

    def set(self, bars):
        self.CurrentBar = len(bars)
        # MultiCharts razí bar časom ZATVORENIA
        self.Time = Series(FakeDateTime.from_ms(b.time + 0) for b in bars)
        self.Open = Series(b.open for b in bars)
        self.High = Series(b.high for b in bars)
        self.Low = Series(b.low for b in bars)
        self.Close = Series(b.close for b in bars)
        self.Volume = Series(b.volume for b in bars)


class FakeCtx:
    def __init__(self, bars: FakeBars, data2: FakeBars | None = None):
        self.Bars = bars
        self._data2 = data2
        self.MaxDataStream = 2 if data2 is not None else 1
        self.StrategyInfo = types.SimpleNamespace(MarketPosition=0)
        self.OrderCreator = FakeOrderCreator()
        self.DrwRectangle = FakeDrwFactory("rect")
        self.DrwTrendLine = FakeDrwFactory("line")
        self.DrwText = FakeDrwFactory("text")
        self.lines: list[str] = []
        self.Output = types.SimpleNamespace(WriteLine=lambda fmt, *a: self.lines.append(fmt))

    def BarsOfData(self, n):
        if n == 2 and self._data2 is not None:
            return self._data2
        raise RuntimeError("no such data stream")


@pytest.fixture
def fake_dotnet(monkeypatch, tmp_path):
    # log študie do tmp — testy nesmú písať do skutočného %LOCALAPPDATA%/tradebot/multicharts.log
    monkeypatch.setenv("TRADEBOT_MC_LOG", str(tmp_path / "multicharts.log"))
    pl = types.ModuleType("PowerLanguage")
    for name, obj in {
        "ChartPoint": ChartPoint, "SOrderParameters": SOrderParameters, "Contracts": Contracts,
        "OrderExit": OrderExit, "EOrderAction": EOrderAction, "EResolution": EResolution, "InputInfo": InputInfo,
    }.items():
        setattr(pl, name, obj)
    system = types.ModuleType("System")
    system.DateTime, system.Array = FakeDateTime, FakeArray
    drawing = types.ModuleType("System.Drawing")
    drawing.Color = FakeColor
    system.Drawing = drawing
    for name, mod in {"PowerLanguage": pl, "System": system, "System.Drawing": drawing}.items():
        monkeypatch.setitem(sys.modules, name, mod)
    yield


# --------------------------------------------------------------------------- #
# pomocné
# --------------------------------------------------------------------------- #


def closed(ts_open: int, tf: int, o=100.0, h=101.0, low=99.0, c=100.5, v=10.0):
    """Bar tak, ako ho dá MultiCharts: `time` = čas zatvorenia."""
    from tradebot.core import Bar

    return Bar(time=ts_open + tf * MIN, open=o, high=h, low=low, close=c, volume=v)


def plan(direction=Direction.LONG, entry=100.0, sl=99.0, tp=102.0, qty=3.0) -> TradePlan:
    return TradePlan(direction=direction, entry=entry, stop_loss=sl, take_profit=tp, qty=qty, sl_distance=abs(entry - sl))


def live(order_id: str, market=False, **kw) -> LiveOrder:
    p = plan(**kw)
    return LiveOrder(order_id=order_id, source_id=1, direction=p.direction, plan=p, market=market)


def cfg() -> IBSConfig:
    return IBSConfig(
        sess1On=True, sess1TZ="UTC", weekdaysOnly=False,
        sess1ZoneStartH=0, sess1ZoneEndH=23, sess1TradeStartH=0, sess1TradeEndH=23,
    )


def make_signal(monkeypatch, ctx, strategy_key="ibs"):
    from tradebot.adapters.multicharts import signal as sig_mod

    class Sig(sig_mod.TradebotSignal):
        STRATEGY_KEY = strategy_key

    monkeypatch.setattr(sig_mod, "load_profile", lambda profile, strategy=None: (cfg(), MNQ))
    s = Sig()
    assert s.GetInputs() == [] and s.GetInputValue("x") is None
    s.SetInputValue("x", 1)
    s.Create(ctx)
    s.StartCalc()
    return s


# --------------------------------------------------------------------------- #
# prevody
# --------------------------------------------------------------------------- #


def test_dotnet_ms_berie_ticks_a_python_datetime():
    from tradebot.adapters.multicharts.signal import dotnet_ms

    assert dotnet_ms(FakeDateTime(2025, 1, 6, 0, 3)) == T0 + 3 * MIN
    assert dotnet_ms(datetime(2025, 1, 6, 0, 3)) == T0 + 3 * MIN  # naivný = UTC
    assert dotnet_ms(datetime(2025, 1, 6, 1, 3, tzinfo=timezone(__import__("datetime").timedelta(hours=1)))) == T0 + 3 * MIN
    with pytest.raises(TypeError):
        dotnet_ms("2025-01-06")


def test_resolution_minutes_pozna_minuty_hodiny_a_odmietne_ostatne():
    from tradebot.adapters.multicharts.signal import resolution_minutes

    assert resolution_minutes(FakeBars(3, []).Info) == 3
    assert resolution_minutes(FakeBars(60, [], res_type="EResolution.Hour", size=1).Info) == 60
    assert resolution_minutes(FakeBars(1, [], res_type="Second", size=120).Info) == 2
    with pytest.raises(ValueError, match="Tick"):
        resolution_minutes(FakeBars(1, [], res_type="EResolution.Tick", size=100).Info)
    with pytest.raises(ValueError, match="celý počet"):
        resolution_minutes(FakeBars(1, [], res_type="Second", size=90).Info)


# --------------------------------------------------------------------------- #
# študia
# --------------------------------------------------------------------------- #


def test_create_vyrobi_cely_pool_orderov_naraz(fake_dotnet, monkeypatch):
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    s = make_signal(monkeypatch, ctx)
    names = [o.params.Name for o in ctx.OrderCreator.created]
    assert names.count("tb_sl") == 2 and names.count("tb_tp") == 2 and names.count("tb_session_end") == 2
    assert "tb_long_0" in names and "tb_short_3" in names and "tb_long_mkt" in names
    exits = [o for o in ctx.OrderCreator.created if o.params.Name == "tb_sl"]
    assert {o.params.Action for o in exits} == {"Sell", "BuyToCover"}
    assert all(o.params.ExitTypeInfo == "FromAll" and o.params.Lots == "Default" for o in exits)
    entries = [o for o in ctx.OrderCreator.created if o.params.Name.startswith("tb_long_")]
    assert all(o.params.Lots == "UserSpecified" for o in entries)
    assert s.chart_tf == 3 and any("graf 3m" in line for line in ctx.lines)


def test_bar_ma_cas_otvorenia_a_prvy_bar_sa_zahlasi(fake_dotnet, monkeypatch):
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    s = make_signal(monkeypatch, ctx)
    seen = []
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: seen.append(bar) or BarOutput())
    monkeypatch.setattr(s.runner, "last_ts", None)
    s.CalcBar()
    assert seen[0].time == T0 and seen[0].close == 100.5
    assert any("prvy bar grafu" in line and "otvorenie 2025-01-06 00:00 UTC" in line for line in ctx.lines)


def test_bez_data2_sa_zahlasi_chyba_a_htf_sa_nekrmi(fake_dotnet, monkeypatch):
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    s = make_signal(monkeypatch, ctx)
    assert any("CHYBA - na grafe nie je Data2" in line for line in ctx.lines)
    fed = []
    monkeypatch.setattr(s.runner, "feed_htf", lambda bar: fed.append(bar))
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput())
    s.CalcBar()
    assert fed == []


def test_data2_krmi_uzavrety_5m_bar_s_casom_otvorenia(fake_dotnet, monkeypatch):
    d2 = FakeBars(5, [closed(T0, 5, c=1.0), closed(T0 + 5 * MIN, 5, c=2.0)])
    ctx = FakeCtx(FakeBars(3, [closed(T0 + 6 * MIN, 3)]), data2=d2)
    s = make_signal(monkeypatch, ctx)
    assert not any("nie je Data2" in line for line in ctx.lines)
    assert any("MaxDataStream=2" in line and "Data2=NAS100 5 Minute" in line for line in ctx.lines)
    fed = []
    monkeypatch.setattr(s.runner, "feed_htf", lambda bar: fed.append(bar))
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput())
    s.CalcBar()
    assert len(fed) == 1 and fed[0].time == T0 and fed[0].close == 1.0  # offset [1] = uzavretý bar


def test_vstupy_idu_cez_pool_s_menom_pri_send_a_slot_drzi_kym_order_zije(fake_dotnet, monkeypatch):
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    s = make_signal(monkeypatch, ctx)
    out = BarOutput(entries=[live("LONG_7", entry=100.25, qty=3.4), live("LONG_9", entry=99.5, qty=0.2)])
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: out)
    s.CalcBar()
    o0, o1 = s._orders["long_limit_0"], s._orders["long_limit_1"]
    assert o0.sent == [("LONG_7", 100.25, 3)]
    assert o1.sent == [("LONG_9", 99.5, 1)]  # qty < 1 sa podrží na 1 lot

    # ďalší bar: LONG_7 zmizol, LONG_9 ostáva v tom istom slote, nový ide do uvoľneného
    out2 = BarOutput(entries=[live("LONG_9", entry=99.5), live("SHORT_2", direction=Direction.SHORT, entry=101.0, sl=102.0, tp=99.0)])
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: out2)
    ctx.Bars.set([closed(T0, 3), closed(T0 + 3 * MIN, 3)])
    s.CalcBar()
    assert s._slots == {"LONG_9": "long_limit_1", "SHORT_2": "short_limit_0"}
    assert s._orders["short_limit_0"].sent == [("SHORT_2", 101.0, 3)]
    assert len(o0.sent) == 1  # slot 0 sa tento bar neposlal


def test_so_vstupom_idu_aj_jeho_sl_tp(fake_dotnet, monkeypatch):
    """Exit ordre v tom istom bare ako vstup — inak by MultiCharts minul TP/SL vo vstupnom bare."""
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    s = make_signal(monkeypatch, ctx)
    out = BarOutput(entries=[live("LONG_7", entry=100.0, sl=99.0, tp=102.0),
                             live("SHORT_2", direction=Direction.SHORT, entry=101.0, sl=102.0, tp=99.0)])
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: out)
    s.CalcBar()
    assert s._orders["sl_long"].sent == [(99.0,)] and s._orders["tp_long"].sent == [(102.0,)]
    assert s._orders["sl_short"].sent == [(102.0,)] and s._orders["tp_short"].sent == [(99.0,)]


def test_market_vstup_a_plny_pool(fake_dotnet, monkeypatch):
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    s = make_signal(monkeypatch, ctx)
    s.ENTRY_POOL = 4
    entries = [live(f"LONG_{i}") for i in range(5)] + [live("PB_1", market=True, qty=2)]
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput(entries=entries))
    s.CalcBar()
    assert s._orders["long_market_0"].sent == [("PB_1", 2)]
    assert sum(len(s._orders[f"long_limit_{i}"].sent) for i in range(4)) == 4
    assert any("viac nez 4 zivych long limit" in line for line in ctx.lines)


def test_vystupy_a_koniec_seansy(fake_dotnet, monkeypatch):
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    s = make_signal(monkeypatch, ctx)
    ctx.StrategyInfo.MarketPosition = 3
    p = plan(entry=100.0, sl=99.0, tp=102.0)
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput(exit_plan=p, exit_stop=99.6))
    s.CalcBar()
    assert s._orders["sl_long"].sent == [(99.6,)] and s._orders["tp_long"].sent == [(102.0,)]

    ctx.StrategyInfo.MarketPosition = -3
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput(exit_plan=None, close_session=True))
    s.CalcBar()
    assert s._orders["end_short"].sent == [()] and s._orders["end_short"].kind == "market_this_bar"
    assert s._orders["sl_short"].sent == []  # pri zatvorení seansy sa SL/TP neposielajú

    ctx.StrategyInfo.MarketPosition = 0
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput(close_session=True))
    s.CalcBar()
    assert s._orders["end_long"].sent == [] and s._orders["end_short"].sent == [()]  # bez pozicie nic


def test_kreslenie_kotvi_na_cas_zatvorenia_a_destroy_zmaze(fake_dotnet, monkeypatch):
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    s = make_signal(monkeypatch, ctx)
    box = DrawBox(kind=DrawKind.IMB_BOX, x1_ms=T0, y1=101.0, x2_ms=T0 + 6 * MIN, y2=99.0,
                  border_color="#ff0000", fill_color="#00ff0080", obj_id="z1")
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput(drawings=[box]))
    s.CalcBar()
    rect = ctx.DrwRectangle.objects[0]
    assert rect.Begin.Time.ms == T0 + 3 * MIN and rect.Begin.Price == 101.0  # +TF grafu
    assert rect.End.Time.ms == T0 + 9 * MIN
    assert rect.Color == ("rgb", 255, 0, 0) and rect.FillColor == ("rgb", 0, 255, 0)

    upd = DrawUpdate(obj_id="z1", field="x2_ms", value=T0 + 9 * MIN)
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput(drawings=[upd]))
    s.CalcBar()
    assert rect.End.Time.ms == T0 + 12 * MIN and rect.End.Price == 99.0

    s.Destroy()
    assert rect.deleted


def test_no_draw_vypne_kreslenie_a_odmietnuty_order_sa_zaloguje(fake_dotnet, monkeypatch):
    from tradebot.adapters.multicharts import signal as sig_mod

    monkeypatch.setattr(sig_mod.TradebotSignal, "NO_DRAW", True)
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    s = make_signal(monkeypatch, ctx)
    box = DrawBox(kind=DrawKind.IMB_BOX, x1_ms=T0, y1=101.0, x2_ms=T0 + 6 * MIN, y2=99.0,
                  border_color="#ff0000", fill_color=None, obj_id="z1")
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput(drawings=[box]))
    s.CalcBar()
    assert ctx.DrwRectangle.objects == [] and s._stats["drawings"] == 1
    s.OnOrderRejected("Buy", "Enter", 27, 100.0, 0.0)
    assert any("ORDER ODMIETNUTY" in line and "lots=27" in line for line in ctx.lines)


def test_fpu_masky_sa_vratia_a_zmena_sa_zaloguje(fake_dotnet, monkeypatch):
    from tradebot.adapters.multicharts import signal as sig_mod

    calls = iter([(0x0008001F, False), (0x00080000, True), (0x00080000, True), (0x00080010, True)])
    monkeypatch.setattr(sig_mod, "fpu_mask_exceptions", lambda: next(calls))
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    s = make_signal(monkeypatch, ctx)  # StartCalc: maskované -> nič
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput())
    s.CalcBar()  # 0x00080000 odmaskované -> hláška
    s.CalcBar()  # rovnaká hodnota -> bez ďalšej hlášky
    s.CalcBar()  # iná hodnota -> hláška
    fpu_lines = [line for line in ctx.lines if "FPU vynimky boli odmaskovane" in line]
    assert len(fpu_lines) == 2 and "0x00080000" in fpu_lines[0] and "0x00080010" in fpu_lines[1]


def test_startcalc_zabudne_stav_minuleho_behu(fake_dotnet, monkeypatch):
    """MultiCharts pri prepočte volá len StartCalc — počítadlo obchodov musí začať odznova."""
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    ctx.TotalTrades = 0
    ctx.StrategyInfo.ClosedEquity = 0.0
    s = make_signal(monkeypatch, ctx)
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput())
    s._last_entry = ("LONG_1", 2.0, 100.0)
    s.CalcBar()
    ctx.TotalTrades, ctx.StrategyInfo.ClosedEquity = 5, 50.0   # minulý beh skončil na 5 obchodoch
    s.CalcBar()
    assert s._last_closed_trades == 5

    s.StartCalc()                                                # prepočet: MultiCharts začína od 0
    assert s._last_closed_trades is None and s._last_position == 0.0 and s._open_entry is None
    ctx.TotalTrades, ctx.StrategyInfo.ClosedEquity = 0, 0.0
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput())
    s._last_entry = ("LONG_7", 3.0, 100.0)
    s.CalcBar()
    ctx.TotalTrades, ctx.StrategyInfo.ClosedEquity = 1, 12.5
    s.CalcBar()
    trade_lines = [line for line in _read_log(s) if "[trade]" in line]
    assert trade_lines and "n=1" in trade_lines[-1] and "order=LONG_7" in trade_lines[-1] and "pnl=12.50" in trade_lines[-1]


def _read_log(s) -> list[str]:
    return s._log_path.read_text(encoding="utf-8").splitlines() if s._log_path.exists() else []


def test_output_zdvoji_zlozene_zatvorky(fake_dotnet, monkeypatch):
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    s = make_signal(monkeypatch, ctx)
    s._out("plan {'a': 1}")
    assert ctx.lines[-1] == "plan {{'a': 1}}"
