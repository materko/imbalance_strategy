"""Spoločný vstupný model — potvrdenie vstupu sviečkou (`tradebot.core.entry_confirm`) — na jednoduchom engine."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.engine import EngineOutput
from tradebot.core.entry_confirm import EntryConfirm, EntryConfirmEngine, is_imbalance, is_pinbar, wrap_entry_confirm
from tradebot.core.entry_order import EntryOrderEngine, EntryOrderType
from tradebot.core.orders import OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies import STRATEGIES

MNQ = INSTRUMENTS["mnq_databento"]
CTX = MarketContext(in_trade_window=True)


@dataclass
class _Cfg:
    entryConfirm: EntryConfirm = EntryConfirm.PINBAR
    confirmBars: int = 3
    confirmImbMinAtr: float = 0.0
    confirmPbWickPct: int = 60
    confirmPbBodyPct: int = 30
    entryOrderType: EntryOrderType = EntryOrderType.LIMIT
    limitOffsetPct: int = 50
    limitValidBars: int = 2
    limitKeepRR: bool = True


class _Eng:
    """Na bare s časom 0 pošle market long: vstup 110, stop 100, cieľ 130 (RR 2). Inak nič."""
    inst = MNQ

    def __init__(self, at=(0,)):
        self.at = at

    def on_bar(self, bar, htf=None, ctx=None):
        out = EngineOutput()
        if bar.time in self.at:
            plan = TradePlan(direction=Direction.LONG, entry=110.0, stop_loss=100.0, take_profit=130.0, qty=10.0,
                             sl_distance=10.0)
            out.orders.append(OrderIntent(OrderAction.ENTRY, f"e{bar.time}", 0, direction=Direction.LONG, plan=plan,
                                          order_type=OrderType.MARKET))
        return out


def _bar(t, o, h, lo, c):
    return Bar(time=t, open=o, high=h, low=lo, close=c, volume=1)


PLAIN = (108, 111, 107, 110)          # plné telo, žiadny knôt
PIN = (107.8, 108, 104, 108)          # knôt dole 3,8 zo 4; telo 0,2


def test_none_necha_engine_bez_obalu():
    e = _Eng()
    assert wrap_entry_confirm(e, _Cfg(entryConfirm=EntryConfirm.NONE)) is e
    assert isinstance(wrap_entry_confirm(e, _Cfg()), EntryConfirmEngine)


def test_pin_bar_a_imbalance():
    assert is_pinbar(_bar(0, *PIN), True, 60, 30) and not is_pinbar(_bar(0, *PIN), False, 60, 30)
    b2, b1, b0 = _bar(0, 100, 101, 99, 100.5), _bar(1, 100.5, 104, 100.4, 103.8), _bar(2, 103.8, 105, 102, 104.5)
    assert is_imbalance(b0, b1, b2, True) and not is_imbalance(b0, b1, b2, False)
    assert not is_imbalance(b0, b1, b2, True, min_gap=1.5), "medzera 1,0 je menej než 1,5"


def test_vstup_sa_podrzi_a_pride_az_na_pin_bare_so_zachovanym_stopom_rr_a_rizikom():
    w = EntryConfirmEngine(_Eng(), _Cfg())
    assert w.on_bar(_bar(0, *PLAIN), None, CTX).orders == [], "signálna sviečka nie je pin bar — čaká sa"
    o = w.on_bar(_bar(1, *PIN), None, CTX).orders[0]
    assert o.action is OrderAction.ENTRY and o.order_type is OrderType.MARKET and o.order_id == "e0"
    assert (o.plan.entry, o.plan.stop_loss, o.plan.take_profit) == (108, 100, 124)      # RR 2 zo 108
    assert abs(o.plan.qty - 10 * 10 / 8) < 1e-9
    assert w.on_bar(_bar(2, *PIN), None, CTX).orders == [], "jeden signál = jeden vstup"


def test_signalna_sviecka_sama_moze_byt_potvrdenim():
    w = EntryConfirmEngine(_Eng(), _Cfg())
    assert len(w.on_bar(_bar(0, *PIN), None, CTX).orders) == 1


def test_bez_potvrdenia_signal_prepadne():
    w = EntryConfirmEngine(_Eng(), _Cfg(confirmBars=2))
    for t in (0, 1):
        assert w.on_bar(_bar(t, *PLAIN), None, CTX).orders == []
    assert w.on_bar(_bar(2, *PIN), None, CTX).orders == [], "pin bar prišiel až tretí bar"


def test_cena_cez_stop_signal_rusi():
    w = EntryConfirmEngine(_Eng(), _Cfg())
    w.on_bar(_bar(0, *PLAIN), None, CTX)
    assert w.on_bar(_bar(1, 108, 109, 99.5, 108.8), None, CTX).orders == []      # low pod stopom 100
    assert w.on_bar(_bar(2, *PIN), None, CTX).orders == []


def test_imbalance_ako_potvrdenie():
    w = EntryConfirmEngine(_Eng(at=(1,)), _Cfg(entryConfirm=EntryConfirm.IMBALANCE))
    w.on_bar(_bar(0, 104, 105, 103, 104.5), None, CTX)
    assert w.on_bar(_bar(1, 104.5, 108, 104.4, 107.8), None, CTX).orders == []
    o = w.on_bar(_bar(2, 107.8, 110, 106, 109.5), None, CTX).orders[0]           # low 106 > high 105 prvej sviečky
    assert o.plan.entry == 109.5 and o.plan.stop_loss == 100


def test_limitka_strategie_sa_nemeni():
    class _Lim(_Eng):
        def on_bar(self, bar, htf=None, ctx=None):
            out = super().on_bar(bar, htf, ctx)
            out.orders = [OrderIntent(o.action, o.order_id, 0, direction=o.direction, plan=o.plan,
                                      order_type=OrderType.LIMIT) for o in out.orders]
            return out
    w = EntryConfirmEngine(_Lim(), _Cfg())
    assert w.on_bar(_bar(0, *PLAIN), None, CTX).orders[0].order_type is OrderType.LIMIT


def test_potvrdeny_vstup_ide_aj_limitkou_spat_do_potvrdzovacej_sviecky():
    w = EntryOrderEngine(EntryConfirmEngine(_Eng(), _Cfg()), _Cfg())
    assert w.on_bar(_bar(0, *PLAIN), None, CTX).orders == []
    o = w.on_bar(_bar(1, *PIN), None, CTX).orders[0]
    assert o.order_type is OrderType.LIMIT and o.plan.entry == 106 and o.plan.stop_loss == 100      # 108 − 50 % zo 4


#: stratégie s vlastným vstupným modelom IBS imbalance / pin bar — spoločný obal nemajú
_OWN = {"ibs", "ibsentry", "ibsfvg", "ibsnet", "ibszones", "jss", "fibo", "svp", "liquidity"}


@pytest.mark.parametrize("key", sorted(STRATEGIES))
def test_kazda_strategia_ma_vstupny_model_ibs_a_pin_bar(key):
    cfg = STRATEGIES[key].config_cls()
    if key in _OWN:
        text = " ".join(str(v) for v in type(cfg).ENUM_FIELDS.values()) + " ".join(vars(cfg))
        assert "EntryModel" in text or "enablePinBarEntry" in text
        return
    assert EntryConfirm(cfg.entryConfirm) is EntryConfirm.NONE, "default nemení správanie stratégie"
    assert "entryConfirm" in STRATEGIES[key].param_meta
