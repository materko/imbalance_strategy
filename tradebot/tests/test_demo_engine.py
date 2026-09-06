"""Ukážková stratégia Demo Donchian Breakout: engine na syntetických baroch.

Cieľ nie je edge, ale to, že druhá stratégia prejde celým rámcom: config z Pine,
engine cez generický `EngineOutput`, ordery s `TradePlan`, registrované druhy kresieb
a beh cez generický Freqtrade runner bez informatívneho TF.
"""

from __future__ import annotations

import pytest

from tradebot.adapters.freqtrade import EngineRunner
from tradebot.core import BTCUSDT_BINANCE, Bar, DrawKind, MarketContext, OrderAction
from tradebot.core.types import Direction, OrderType
from tradebot.strategies.demo_breakout import DemoBreakoutConfig, DemoBreakoutEngine, ExitMode

T0 = 1_756_684_800_000
MIN5 = 300_000


def bar(i: int, o=100.0, h=101.0, low=99.0, c=100.5, v=10.0) -> Bar:
    return Bar(time=T0 + i * MIN5, open=o, high=h, low=low, close=c, volume=v)


def warm(engine: DemoBreakoutEngine, n: int = 40) -> None:
    for i in range(n):
        engine.on_bar(bar(i), None, MarketContext(in_trade_window=True))


def test_defaults_validate_and_required_history():
    cfg = DemoBreakoutConfig()
    assert cfg.exitMode is ExitMode.OPPOSITE and cfg.slAtrMult.unit == "atr"
    engine = DemoBreakoutEngine(cfg, BTCUSDT_BINANCE, 5)
    assert engine.required_history == cfg.channelLen + cfg.atrLen + 8


def test_breakout_long_gives_market_entry_with_sl_below_and_tp_above():
    engine = DemoBreakoutEngine(DemoBreakoutConfig(), BTCUSDT_BINANCE, 5)
    warm(engine)
    out = engine.on_bar(bar(40, o=100.5, h=104.0, low=100.0, c=103.5), None, MarketContext(in_trade_window=True))
    entries = [o for o in out.orders if o.action is OrderAction.ENTRY]
    assert len(entries) == 1
    intent = entries[0]
    assert intent.direction is Direction.LONG and intent.order_type is OrderType.MARKET
    plan = intent.plan
    assert plan.stop_loss < plan.entry == 103.5 < plan.take_profit
    assert plan.take_profit - plan.entry == pytest.approx((plan.entry - plan.stop_loss) * 2.0, rel=1e-6)
    assert plan.qty > 0
    kinds = {o.kind for o in out.drawings}
    assert DrawKind.DEMO_ENTRY in kinds and DrawKind.DC_UPPER in kinds and DrawKind.DC_LOWER in kinds
    for k in kinds:
        assert DrawKind(k.value) is k  # registrované


def test_short_disabled_when_allow_short_off():
    engine = DemoBreakoutEngine(DemoBreakoutConfig(allowShort=False), BTCUSDT_BINANCE, 5)
    warm(engine)
    out = engine.on_bar(bar(40, o=99.5, h=100.0, low=96.0, c=96.5), None, MarketContext(in_trade_window=True))
    assert not [o for o in out.orders if o.action is OrderAction.ENTRY]
    engine2 = DemoBreakoutEngine(DemoBreakoutConfig(allowShort=True), BTCUSDT_BINANCE, 5)
    warm(engine2)
    out2 = engine2.on_bar(bar(40, o=99.5, h=100.0, low=96.0, c=96.5), None, MarketContext(in_trade_window=True))
    assert [o.direction for o in out2.orders if o.action is OrderAction.ENTRY] == [Direction.SHORT]


def test_opposite_breakout_closes_open_position_only_in_opposite_mode():
    for mode, expect in ((ExitMode.OPPOSITE, True), (ExitMode.TP_ONLY, False)):
        engine = DemoBreakoutEngine(DemoBreakoutConfig(exitMode=mode), BTCUSDT_BINANCE, 5)
        warm(engine)
        ctx = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({"demo:1"}))
        out = engine.on_bar(bar(40, o=99.5, h=100.0, low=96.0, c=96.5), None, ctx)
        assert out.close_session is expect
        assert bool([o for o in out.orders if o.action is OrderAction.CLOSE]) is expect


def test_no_channel_drawings_when_show_channel_off():
    engine = DemoBreakoutEngine(DemoBreakoutConfig(showChannel=False), BTCUSDT_BINANCE, 5)
    warm(engine)
    out = engine.on_bar(bar(40), None, MarketContext(in_trade_window=True))
    assert not [o for o in out.drawings if o.kind in (DrawKind.DC_UPPER, DrawKind.DC_LOWER)]


def test_generic_runner_runs_demo_without_htf():
    runner = EngineRunner(DemoBreakoutConfig(), BTCUSDT_BINANCE, 5)
    assert runner.spec.key == "demo_breakout" and runner.htf is None
    for i in range(40):
        runner.process(bar(i), runner.window_for(T0 + i * MIN5))
    row = runner.process(bar(40, o=100.5, h=104.0, low=100.0, c=103.5), None)
    assert row.enter_long == 1 and row.in_trade_window is True and row.stop_loss < row.entry < row.take_profit
    assert runner.signal_at(T0 + 40 * MIN5) is row
