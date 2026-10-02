"""Fibo: engine na syntetických baroch.

Testuje sa mechanika: noha od swing dna po swing vrchol sa použije až po potvrdení vrcholu,
vstup len pri návrate do zóny úrovní a na potvrdzovaciu sviečku, stop za začiatok nohy alebo
za extrém návratu, cieľ na extenzii, a že prerazenie 100 % setup ruší.
"""

from __future__ import annotations

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction
from tradebot.strategies.fibo import FiboConfig, FiboEngine

T0 = 1_756_821_600_000
MIN5 = 300_000
OKNO = MarketContext(in_trade_window=True)
MNQ = INSTRUMENTS["mnq_databento"]


def _cfg(**kw) -> FiboConfig:
    base = dict(swingTF=5, swingLen=2, atrLen=3, legMinAtr=0.0, requireBreak=False, levelTolAtr=0.0,
                slBufferAtr=0.0, entryModel="pinbar", minRR=0.0)
    base.update(kw)
    return FiboConfig(**base)


def _bar(i: int, o: float, h: float, lo: float, c: float) -> Bar:
    return Bar(time=T0 + i * MIN5, open=o, high=h, low=lo, close=c, volume=10.0)


#: dno 100 (index 2), vrchol 110 (index 5), návrat na 105 (50 %) — vrchol sa potvrdí na indexe 7
_LEG = [(103, 104, 102, 103), (103, 103.5, 101, 101.5), (101.5, 102, 100, 101), (101, 104, 100.8, 103.5),
        (103.5, 107, 103, 106.5), (106.5, 110, 106, 109.5), (109.5, 109.8, 107, 107.5), (107.5, 108, 105, 105.5)]
_PIN = (105.5, 106, 104.5, 105.9)        # pin bar: knôt 1,0 z rozsahu 1,5; dno návratu 104,5 = 55 %


def _run(e, rows, start=0):
    return [e.on_bar(_bar(start + i, *r), None, OKNO) for i, r in enumerate(rows)]


def _entries(outs):
    return [o for out in outs for o in out.orders if o.action is OrderAction.ENTRY]


def test_noha_sa_pouzije_az_po_potvrdeni_vrcholu():
    e = FiboEngine(_cfg(), MNQ, 5)
    _run(e, _LEG[:7])
    assert not e.setups, "vrchol má vpravo len jeden bar — ešte nie je swing"
    _run(e, _LEG[7:], start=7)
    s = e.setups[Direction.LONG]
    assert (s.start, s.end, s.extreme) == (100, 110, 105) and abs(s.depth - 0.5) < 1e-9


def test_pin_bar_v_zone_je_long_so_stopom_za_nohu_a_cielom_na_extenzii_27():
    e = FiboEngine(_cfg(), MNQ, 5)
    _run(e, _LEG)
    o = _entries(_run(e, [_PIN], start=len(_LEG)))[0]
    assert o.direction is Direction.LONG and o.plan.entry == 106
    assert o.plan.stop_loss == 100 and abs(o.plan.take_profit - 112.75) < 0.26      # 110 + 27 % z 10, na tick
    assert Direction.LONG not in e.setups, "jedna noha = jeden obchod"


def test_stop_za_extrem_navratu():
    e = FiboEngine(_cfg(slMode="pullback"), MNQ, 5)
    _run(e, _LEG)
    assert _entries(_run(e, [_PIN], start=len(_LEG)))[0].plan.stop_loss == 104.5


def test_prerazenie_100_percent_setup_zrusi():
    e = FiboEngine(_cfg(), MNQ, 5)
    _run(e, _LEG)
    outs = _run(e, [(105.5, 105.6, 99.5, 104), _PIN], start=len(_LEG))
    assert not _entries(outs) and Direction.LONG not in e.setups


def test_plytky_navrat_a_rezim_levels():
    plytky = list(_LEG[:6]) + [(109.5, 109.8, 108.6, 109), (109, 109.5, 108.4, 108.8)]     # návrat 16 %
    e = FiboEngine(_cfg(), MNQ, 5)
    _run(e, plytky)
    assert not _entries(_run(e, [(108.8, 109, 108.3, 108.9)], start=len(plytky))), "pod 38,2 % sa nevstupuje"
    e = FiboEngine(_cfg(levelMode="levels"), MNQ, 5)                                    # 55 % nie je pri 50 ani 61,8
    _run(e, _LEG)
    assert not _entries(_run(e, [_PIN], start=len(_LEG)))
