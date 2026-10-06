"""Spoločný filter trendu (`tradebot.core.entry_filter`) na jednoduchom engine."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.engine import EngineOutput
from tradebot.core.entry_filter import EntryFilterEngine, TrendFilter, wrap_entry_filter
from tradebot.core.orders import OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.core.warmup import Warmup
from tradebot.strategies import STRATEGIES

MNQ = INSTRUMENTS["mnq_databento"]
CTX = MarketContext(in_trade_window=True)
MIN5 = 300_000


@dataclass
class _Cfg:
    trendFilter: TrendFilter = TrendFilter.WITH
    trendEmaLen: int = 3
    trendTF: int = 0


class _Eng:
    """Na každom bare pošle market long aj short."""
    inst = MNQ

    def __init__(self):
        self.warmup = Warmup(5)

    def on_bar(self, bar, htf=None, ctx=None):
        out = EngineOutput()
        for d, sl, tp in ((Direction.LONG, bar.close - 10, bar.close + 10), (Direction.SHORT, bar.close + 10, bar.close - 10)):
            plan = TradePlan(direction=d, entry=bar.close, stop_loss=sl, take_profit=tp, qty=1.0, sl_distance=10.0)
            out.orders.append(OrderIntent(OrderAction.ENTRY, f"{d.name}{bar.time}", 0, direction=d, plan=plan,
                                          order_type=OrderType.MARKET))
        return out


def _bar(i, c):
    return Bar(time=i * MIN5, open=c, high=c + 1, low=c - 1, close=c, volume=1)


def _dirs(out):
    return [o.plan.direction for o in out.orders]


def test_off_necha_engine_bez_obalu():
    e = _Eng()
    assert wrap_entry_filter(e, _Cfg(trendFilter=TrendFilter.OFF), 5) is e
    assert isinstance(wrap_entry_filter(e, _Cfg(), 5), EntryFilterEngine)


def test_kym_ema_nie_je_hotova_vstupy_nepusta():
    w = EntryFilterEngine(_Eng(), _Cfg(), 5)
    assert w.on_bar(_bar(0, 100), None, CTX).orders == [] and w.on_bar(_bar(1, 101), None, CTX).orders == []


def test_s_trendom_long_nad_ema_short_pod_nou():
    w = EntryFilterEngine(_Eng(), _Cfg(), 5)
    for i, c in enumerate((100, 100, 100)):
        w.on_bar(_bar(i, c), None, CTX)
    assert w.ema == 100
    assert _dirs(w.on_bar(_bar(3, 104), None, CTX)) == [Direction.LONG]      # EMA 102, zavretie nad ňou
    assert _dirs(w.on_bar(_bar(4, 90), None, CTX)) == [Direction.SHORT]      # EMA 96, zavretie pod ňou


def test_proti_trendu_naopak():
    w = EntryFilterEngine(_Eng(), _Cfg(trendFilter=TrendFilter.AGAINST), 5)
    for i, c in enumerate((100, 100, 100)):
        w.on_bar(_bar(i, c), None, CTX)
    assert _dirs(w.on_bar(_bar(3, 104), None, CTX)) == [Direction.SHORT]


def test_vyssi_tf_berie_len_uzavrete_bary():
    w = EntryFilterEngine(_Eng(), _Cfg(trendEmaLen=2, trendTF=15), 5)
    closes = [100, 101, 102, 110, 111, 112]            # dva 15m bary: zavretia 102 a 112
    for i, c in enumerate(closes[:5]):
        w.on_bar(_bar(i, c), None, CTX)
    assert w.ema is None, "druhý 15m bar ešte nie je uzavretý"
    w.on_bar(_bar(5, closes[5]), None, CTX)
    assert w.ema == 107


def test_predhistoria_ide_seedom_do_warmupu_enginu():
    e = _Eng()
    w = EntryFilterEngine(e, _Cfg(trendEmaLen=3, trendTF=15), 5)
    need = e.warmup.seeds[-1]
    assert need.tf_minutes == 15 and need.bars >= 3
    need.seed([_bar(0, 100), _bar(3, 100), _bar(6, 100)], None)
    assert w.ema == 100 and _dirs(w.on_bar(_bar(9, 105), None, CTX)) == [Direction.LONG]


#: stratégie s vlastným filtrom trendu — spoločný obal nemajú
_OWN = {"ibs", "ibsentry", "ibsfvg", "ibsnet", "ibszones", "liquidity"}


@pytest.mark.parametrize("key", sorted(set(STRATEGIES) - _OWN))
def test_kazda_strategia_ma_filter_trendu(key):
    cfg = STRATEGIES[key].config_cls()
    assert TrendFilter(cfg.trendFilter) is TrendFilter.OFF, "default nemení správanie stratégie"
    assert "trendFilter" in STRATEGIES[key].param_meta


def test_filter_volatility_pokojny_a_rozkyvany_trh():
    from tradebot.core.entry_filter import VolFilter

    @dataclass
    class _V(_Cfg):
        trendFilter: TrendFilter = TrendFilter.OFF
        volFilter: VolFilter = VolFilter.LOW
        volLookback: int = 10

    def bar(i, rng):
        return Bar(time=i * MIN5, open=100, high=100 + rng / 2, low=100 - rng / 2, close=100, volume=1)

    assert isinstance(wrap_entry_filter(_Eng(), _V(), 5), EntryFilterEngine)
    low, high = EntryFilterEngine(_Eng(), _V(), 5), EntryFilterEngine(_Eng(), _V(volFilter=VolFilter.HIGH), 5)
    for i in range(30):
        for w in (low, high):
            w.on_bar(bar(i, 4), None, CTX)
    # pokles volatility: ATR pod priemerom → low púšťa, high nie
    assert len(low.on_bar(bar(30, 1), None, CTX).orders) == 2 and high.on_bar(bar(30, 1), None, CTX).orders == []
    for i in range(31, 36):
        for w in (low, high):
            w.on_bar(bar(i, 20), None, CTX)
    assert low.on_bar(bar(36, 20), None, CTX).orders == [] and len(high.on_bar(bar(36, 20), None, CTX).orders) == 2


from tradebot.core.entry_confirm import EntryConfirm  # noqa: E402
from tradebot.core.entry_order import EntryOrderType  # noqa: E402


@dataclass
class _All(_Cfg):
    """Config so všetkými tromi obalmi (na pickle)."""
    entryConfirm: EntryConfirm = EntryConfirm.ANY
    confirmBars: int = 3
    confirmImbMinAtr: float = 0.0
    confirmPbWickPct: int = 60
    confirmPbBodyPct: int = 30
    entryOrderType: EntryOrderType = EntryOrderType.LIMIT
    limitOffsetPct: int = 50
    limitValidBars: int = 2
    limitKeepRR: bool = True

def test_obaly_vstupov_sa_daju_picklovat():
    """Freqtrade hyperopt prenáša stratégiu medzi procesmi — obal nesmie pri unpickle spadnúť do rekurzie."""
    import pickle
    from tradebot.core.entry_confirm import EntryConfirmEngine
    from tradebot.core.entry_order import EntryOrderEngine

    cfg = _All()
    w = EntryOrderEngine(EntryConfirmEngine(EntryFilterEngine(_Eng(), cfg, 5), cfg), cfg)
    w2 = pickle.loads(pickle.dumps(w))
    assert w2.inst is MNQ and isinstance(w2.engine.engine, EntryFilterEngine)
