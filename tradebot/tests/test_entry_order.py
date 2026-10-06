"""Spoločný typ vstupu market / limit (`tradebot.core.entry_order`) na jednoduchom engine."""

from __future__ import annotations

from dataclasses import dataclass

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.engine import EngineOutput
from tradebot.core.entry_order import EntryOrderEngine, EntryOrderType, wrap_entry_order
from tradebot.core.orders import OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import INSTRUMENTS, Direction, OrderType

MNQ = INSTRUMENTS["mnq_databento"]


@dataclass
class _Cfg:
    entryOrderType: EntryOrderType = EntryOrderType.LIMIT
    limitOffsetPct: int = 50
    limitValidBars: int = 2
    limitKeepRR: bool = True


class _Eng:
    """Na každom bare pošle market long: vstup 110, stop 100, cieľ 130 (RR 2)."""
    inst = MNQ

    def on_bar(self, bar, htf=None, ctx=None):
        out = EngineOutput()
        plan = TradePlan(direction=Direction.LONG, entry=110.0, stop_loss=100.0, take_profit=130.0, qty=10.0, sl_distance=10.0)
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"e{bar.time}", 0, direction=Direction.LONG, plan=plan,
                                      order_type=OrderType.MARKET))
        return out


def _bar(t):
    return Bar(time=t, open=104, high=112, low=104, close=110, volume=1)


def test_market_nechá_engine_bez_obalu():
    e = _Eng()
    assert wrap_entry_order(e, _Cfg(entryOrderType=EntryOrderType.MARKET)) is e


def test_limitka_na_strede_sviecky_so_zachovanym_rr_a_rovnakym_rizikom():
    w = EntryOrderEngine(_Eng(), _Cfg())
    o = w.on_bar(_bar(0), None, MarketContext(in_trade_window=True)).orders[0]
    assert o.order_type is OrderType.LIMIT
    assert o.plan.entry == 106 and o.plan.stop_loss == 100 and o.plan.take_profit == 118   # RR 2 zo 106
    assert abs(o.plan.qty - 10 * 10 / 6) < 1e-9


def test_kym_limitka_caka_dalsie_vstupy_sa_zahodia_a_po_platnosti_sa_zrusi():
    w = EntryOrderEngine(_Eng(), _Cfg())
    ctx = MarketContext(in_trade_window=True)
    away = lambda t: Bar(time=t, open=109, high=112, low=108, close=110, volume=1)   # limitku 106 nedosiahne
    first = w.on_bar(_bar(0), None, ctx).orders
    assert len(first) == 1
    assert w.on_bar(away(1), None, ctx).orders == []
    cancel = w.on_bar(away(2), None, ctx).orders
    assert cancel[0].action is OrderAction.CANCEL and cancel[0].order_id == first[0].order_id
    assert cancel[1].action is OrderAction.ENTRY, "po zrušení môže prísť nový vstup"


def test_cena_prejde_limitkou_a_obchod_sa_zavrie_v_tom_istom_bare_je_vyplnenie():
    w = EntryOrderEngine(_Eng(), _Cfg())
    ctx = MarketContext(in_trade_window=True)
    w.on_bar(_bar(0), None, ctx)
    w.on_bar(_bar(1), None, ctx)             # low 104 ≤ limitka 106 — vyplnená, aj keď po bare je pozícia zase 0
    assert w._pending is None or w._pending[0] != "e0"


class _DrawEng(_Eng):
    """Ako _Eng, ale kreslí TP / SL boxy a štítok vstupu a hlási, čo mu obal povedal."""

    def __init__(self):
        self.seen = []

    def on_bar(self, bar, htf=None, ctx=None):
        from tradebot.core.drawing import DrawBox, DrawKind, DrawLabel
        from tradebot.strategies.svp.drawing import SVP_ENTRY
        self.seen.append((set(ctx.pending_entry_ids), set(ctx.dropped_entry_ids)))
        out = super().on_bar(bar, htf, ctx)
        if bar.time == 0:
            out.drawings += [DrawBox(DrawKind.TP_BOX, 0, 130, 60, 110, "#0f0", obj_id="tp0"),
                             DrawBox(DrawKind.SL_BOX, 0, 110, 60, 100, "#f00", obj_id="sl0"),
                             DrawLabel(SVP_ENTRY, 0, 104, "LONG", "#fff", obj_id="e0lab")]
        else:
            out.orders = []
        return out


def test_nevyplnena_limitka_zmaze_kresbu_a_strategia_sa_to_dozvie():
    from tradebot.core.drawing import DrawBox, DrawDelete, DrawRegistry
    eng = _DrawEng()
    w = EntryOrderEngine(eng, _Cfg())
    ctx = MarketContext(in_trade_window=True)
    reg = DrawRegistry()
    away = lambda t: Bar(time=t, open=109, high=112, low=108, close=110, volume=1)
    o0 = w.on_bar(_bar(0), None, ctx)
    box = next(d for d in o0.drawings if isinstance(d, DrawBox) and d.obj_id == "tp0")
    assert (box.y1, box.y2) == (118, 106), "box sa presunie na ceny limitky"
    reg.extend(o0.drawings)
    for t in (1, 2):
        reg.extend(w.on_bar(away(t), None, ctx).drawings)
    assert not [o for o in reg.objects() if o.obj_id in ("tp0", "sl0", "e0lab")], "obchod nebol — kresba zmizla"
    w.on_bar(away(3), None, ctx)
    assert eng.seen[1][0] == {"e0"} and eng.seen[3][1] == {"e0"}, "čakajúci a potom zahodený vstup"


def test_vyplnena_limitka_posunie_kresbu_na_bar_vyplnenia():
    from tradebot.core.drawing import DrawRegistry
    eng = _DrawEng()
    w = EntryOrderEngine(eng, _Cfg())
    reg = DrawRegistry()
    reg.extend(w.on_bar(_bar(0), None, MarketContext(in_trade_window=True)).drawings)
    reg.extend(w.on_bar(_bar(60_000), None, MarketContext(in_trade_window=True, position_size=1.0)).drawings)
    objs = {o.obj_id: o for o in reg.objects()}
    assert objs["tp0"].x1_ms == 60_000 and objs["e0lab"].x_ms == 60_000
