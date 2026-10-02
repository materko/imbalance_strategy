"""CRT + TBS: engine na syntetických baroch (range 10m z 5m grafu).

Testuje sa mechanika: range je predošlá sviečka vyššieho TF, výber telom (TBS) a knôtom,
vstup až po návrate do rangu, stop za extrém výberu, cieľ opačný koniec / stred rangu,
a že výber oboch strán alebo neskorý výber obchod nedá.
"""

from __future__ import annotations

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.crt import CrtConfig, CrtEngine

T0 = 1_756_821_600_000          # utorok 2025-09-02 14:00 UTC
MIN5 = 300_000
OKNO = MarketContext(in_trade_window=True)
MNQ = INSTRUMENTS["mnq_databento"]


def _cfg(**kw) -> CrtConfig:
    base = dict(rangeTF=10, atrLen=3, slBufferAtr=0.0, entryModel="model1", sweepKind="body", minRR=0.0,
                tpMode="opposite")
    base.update(kw)
    return CrtConfig(**base)


def _bar(i: int, o: float, h: float, lo: float, c: float) -> Bar:
    return Bar(time=T0 + i * MIN5, open=o, high=h, low=lo, close=c, volume=10.0)


#: rozbeh ATR, potom range sviečka 10m (index 8–9): high 110, low 100
_WARM = [(104, 106, 102, 105), (105, 107, 103, 104)] * 4
_RANGE = [(104, 110, 103, 108), (108, 109, 100, 102)]


def _run(e, rows, start=0, ctx=OKNO):
    return [e.on_bar(_bar(start + i, *r), None, ctx) for i, r in enumerate(rows)]


def _entries(outs):
    return [o for out in outs for o in out.orders if o.action is OrderAction.ENTRY]


def _setup(**kw):
    e = CrtEngine(_cfg(**kw), MNQ, 5)
    _run(e, _WARM + _RANGE)
    assert [(s.high, s.low) for s in e.setups][-1] == (110, 100), "range = posledná uzavretá 10m sviečka"
    return e, len(_WARM + _RANGE)


def test_tbs_vyber_telom_nad_crh_a_navrat_je_short_s_cielom_na_crl():
    e, n = _setup()
    outs = _run(e, [(102, 111.5, 101.5, 111),      # zavrie nad CRH 110 — výber telom
                    (111, 112, 107, 108)], start=n)  # späť v rangu, zavrie pod low predošlej (101,5? nie)
    assert not _entries(outs), "model1 chce zavretie za predošlou sviečkou"
    outs = _run(e, [(108, 108.5, 104, 104.5)], start=n + 2)   # medvedia, zavrie pod low 107
    o = _entries(outs)[0]
    assert o.direction is Direction.SHORT and o.order_type is OrderType.MARKET
    assert o.plan.entry == 104.5 and o.plan.stop_loss == 112 and o.plan.take_profit == 100


def test_knot_nad_crh_nestaci_pri_body_ale_staci_pri_wick():
    e, n = _setup()
    rows = [(102, 111.5, 101.5, 109), (109, 109.5, 104, 104.5), (104.5, 105, 101, 101.2)]
    assert not _entries(_run(e, rows, start=n)), "telo za hranicou nezavrelo — TBS nie je"
    e, n = _setup(sweepKind="wick")
    o = _entries(_run(e, rows, start=n))[0]
    assert o.direction is Direction.SHORT and o.plan.stop_loss == 111.5


def test_vyber_oboch_stran_setup_zrusi():
    e, n = _setup(sweepKind="wick")
    outs = _run(e, [(102, 111, 99, 105), (105, 106, 101, 101.5)], start=n)
    assert not _entries(outs)


def test_ciel_v_strede_rangu_a_min_rr():
    e, n = _setup(tpMode="mid")
    rows = [(102, 111.5, 101.5, 111), (111, 112, 107.5, 108), (108, 108.5, 106.5, 107)]
    o = _entries(_run(e, rows, start=n))[0]
    assert o.plan.take_profit == 105
    e, n = _setup(tpMode="mid", minRR=1.0)
    assert not _entries(_run(e, rows, start=n)), "stop 5 bodov, cieľ 2 body — pod 1R sa neobchoduje"


def test_vyber_az_v_tretej_sviecke_vyssieho_tf_sa_nepocita():
    e, n = _setup()
    quiet = [(102, 104, 101, 103), (103, 104, 102, 103)]          # manipulačná sviečka bez výberu
    late = [(103, 111.5, 102.5, 111), (111, 112, 107, 108), (108, 108.5, 104, 104.5)]
    outs = _run(e, quiet + late, start=n)
    assert all(o.plan.take_profit != 100 for o in _entries(outs)), "starý range 100–110 už neplatí"
