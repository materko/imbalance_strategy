"""Pevný počet kontraktov a strop straty (`tradebot.core.entry_sizing`) na jednoduchom engine."""

from __future__ import annotations

from dataclasses import dataclass

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.engine import EngineOutput
from tradebot.core.entry_sizing import EntrySizingEngine, risk_limit, wrap_entry_sizing
from tradebot.core.orders import OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies import STRATEGIES

MNQ = INSTRUMENTS["mnq_databento"]   # 2 $ za bod, krok 1 kontrakt


@dataclass
class _Cfg:
    fixedQty: bool = False
    qty: float = 1.0
    skipOverRisk: bool = True
    riskDollar: float = 100.0


class _Eng:
    """Na každom bare pošle market long so stopom `sl` bodov a veľkosťou z rizika, ako stratégie."""
    inst = MNQ

    def __init__(self, sl: float, qty: float) -> None:
        self.sl, self.qty, self.seen = sl, qty, []

    def on_bar(self, bar, htf=None, ctx=None):
        self.seen.append(ctx)
        out = EngineOutput()
        plan = TradePlan(direction=Direction.LONG, entry=110.0, stop_loss=110.0 - self.sl, take_profit=110.0 + self.sl,
                         qty=self.qty, sl_distance=self.sl)
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"e{bar.time}", 0, direction=Direction.LONG, plan=plan,
                                      order_type=OrderType.MARKET))
        return out


def _bar(t):
    return Bar(time=t, open=104, high=112, low=104, close=110, volume=1)


CTX = MarketContext(in_trade_window=True)


def test_bez_prepinacov_sa_engine_nebali():
    e = _Eng(10, 5)
    assert wrap_entry_sizing(e, _Cfg(skipOverRisk=False, riskDollar=0.0)) is e   # bez rizika nie je čo stropovať


def test_pocet_z_rizika_ma_strop_vzdy():
    """Audit N-LIVE-20: pri počte z rizika podlaha 1 kontrakt riziko neprebije ani bez `skipOverRisk`."""
    w = wrap_entry_sizing(_Eng(80, 1), _Cfg(skipOverRisk=False))
    assert isinstance(w, EntrySizingEngine)
    assert w.on_bar(_bar(0), None, CTX).orders == []


def test_pevny_pocet_bez_prepinaca_obchoduje_aj_nad_riziko():
    """Pevný počet (NOA, TKS, VWAP ORB): nevyužité `riskDollar` obchody nevynechá, kým `skipOverRisk` nie je zapnutý."""
    o = wrap_entry_sizing(_Eng(80, 1), _Cfg(fixedQty=True, qty=1, skipOverRisk=False)).on_bar(_bar(0), None, CTX).orders
    assert len(o) == 1 and o[0].plan.qty == 1
    assert wrap_entry_sizing(_Eng(80, 1), _Cfg(fixedQty=True, qty=1)).on_bar(_bar(0), None, CTX).orders == []


def test_strata_pod_rizikom_prejde_nezmenena():
    # SL 10 bodov × 2 $ = 20 $ na kontrakt, 5 kontraktov = 100 $ = riziko
    o = EntrySizingEngine(_Eng(10, 5), _Cfg()).on_bar(_bar(0), None, CTX).orders
    assert len(o) == 1 and o[0].plan.qty == 5


def test_siroky_stop_pri_ktorom_aj_min_pozicia_prekroci_riziko_sa_vynecha():
    # SL 80 bodov = 160 $ za 1 kontrakt; stratégia dá aspoň min_qty = 1
    e = _Eng(80, 1)
    w = EntrySizingEngine(e, _Cfg())
    assert w.on_bar(_bar(0), None, CTX).orders == []
    w.on_bar(_bar(1), None, CTX)
    assert "e0" in e.seen[-1].dropped_entry_ids   # vnútorné obaly sa dozvedia, že vstup nebol


def test_zlomok_kontraktu_sa_zaokruhli_nadol_ako_u_brokera():
    # po limitke vyjde 5,8 kontraktu; broker by poslal 6 = 120 $ — strop dá 5
    o = EntrySizingEngine(_Eng(10, 5.8), _Cfg()).on_bar(_bar(0), None, CTX).orders
    assert o[0].plan.qty == 5


def test_pevny_pocet_kontraktov():
    o = EntrySizingEngine(_Eng(10, 5), _Cfg(fixedQty=True, qty=3, skipOverRisk=False)).on_bar(_bar(0), None, CTX).orders
    assert o[0].plan.qty == 3


def test_pevny_pocet_nad_riziko_sa_vynecha():
    w = EntrySizingEngine(_Eng(10, 5), _Cfg(fixedQty=True, qty=6))   # 6 × 20 $ = 120 $ > 100 $
    assert w.on_bar(_bar(0), None, CTX).orders == []


def test_bez_rizika_strop_nic_nerobi():
    o = EntrySizingEngine(_Eng(80, 1), _Cfg(riskDollar=0)).on_bar(_bar(0), None, CTX).orders
    assert o[0].plan.qty == 1


def test_kazda_strategia_ma_polia_velkosti_a_riziko():
    for key, spec in STRATEGIES.items():
        cfg = spec.config_cls()
        assert {"fixedQty", "qty", "skipOverRisk"} <= set(cfg.to_dict()), key
        assert spec.risk_field and risk_limit(cfg) == float(getattr(cfg, spec.risk_field)), key
