"""Volume Profile POC: profil a engine na syntetických baroch.

Testuje sa mechanika: objem baru sa rozloží do riadkov, POC je riadok s najväčším objemom a value
area sa nabaľuje od neho; úroveň je POC predošlej seansy; pod POC je limitka short, nad POC long;
po prerazení zavretím je návrat retest; vstupný model čaká po dotyku na sviečku.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.svp import SvpConfig, SvpEngine
from tradebot.strategies.svp.engine import VolumeProfile

NY = ZoneInfo("America/New_York")
MIN5 = 300_000
OKNO = MarketContext(in_trade_window=True)
MNQ = INSTRUMENTS["mnq_databento"]


def _t(day: int, h: int, m: int) -> int:
    return int(datetime(2025, 9, day, h, m, tzinfo=NY).timestamp() * 1000)


def _cfg(**kw) -> SvpConfig:
    base = dict(atrLen=3, awayAtr=1.0, touchTolAtr=0.0, breakBufferAtr=0.0, slMode="points", slPoints=2.0,
                rrRatio=1.5, tradeMode="both", entryModel="touch", retestMaxBars=5, maxTradesPerDay=5)
    base.update(kw)
    return SvpConfig(**base)


def _bar(t: int, o: float, h: float, lo: float, c: float, v: float = 10.0) -> Bar:
    return Bar(time=t, open=o, high=h, low=lo, close=c, volume=v)


#: utorok 2. 9. 2025, seansa: najviac objemu v riadku 101–102 → POC 101,5
_DAY1 = [(100.2, 100.75, 100.0, 100.5, 10), (101.2, 101.75, 101.0, 101.5, 50), (102.2, 102.75, 102.0, 102.5, 20),
         (103.2, 103.75, 103.0, 103.5, 5), (99.2, 99.75, 99.0, 99.5, 15)]


def _day1(e: SvpEngine) -> None:
    for i, (o, h, lo, c, v) in enumerate(_DAY1):
        e.on_bar(_bar(_t(2, 10, 0) + i * MIN5, o, h, lo, c, v), None, OKNO)


def _day2(e: SvpEngine, rows, ctx=OKNO):
    return [e.on_bar(_bar(_t(3, 9, 30) + i * MIN5, *r), None, ctx) for i, r in enumerate(rows)]


def _entries(outs):
    return [o for out in outs for o in out.orders if o.action is OrderAction.ENTRY]


_BELOW = [(96, 96.5, 95.5, 96), (96, 96.5, 95.5, 96), (96, 96.5, 95.5, 96)]        # zavretia hlboko pod POC
_ABOVE = [(107, 107.5, 106.5, 107), (107, 107.5, 106.5, 107), (107, 107.5, 106.5, 107)]


def test_profil_poc_a_value_area():
    p = VolumeProfile(1.0)
    for o, h, lo, c, v in _DAY1:
        p.add(_bar(0, o, h, lo, c, v))
    assert p.poc == 101.5 and p.total == 100
    assert p.value_area(70) == (101.0, 103.0), "50 (POC) + 20 (riadok nad ním) = 70 %"
    assert p.value_area(90) == (99.0, 103.0)


def test_objem_baru_sa_rozlozi_rovnomerne_medzi_low_a_high():
    p = VolumeProfile(1.0)
    p.add(_bar(0, 100, 101.75, 100.0, 101, 20))
    assert p.rows == {100: 10.0, 101: 10.0}


def test_uroven_je_poc_predoslej_seansy():
    e = SvpEngine(_cfg(), MNQ, 5)
    _day1(e)
    assert e.prev is None, "seansa ešte beží"
    _day2(e, _BELOW[:1])
    assert (e.prev.poc, e.prev.val, e.prev.vah) == (101.5, 101.0, 103.0)


def test_pod_poc_je_limitka_short_na_poc():
    e = SvpEngine(_cfg(), MNQ, 5)
    _day1(e)
    o = _entries(_day2(e, _BELOW))[0]
    assert o.direction is Direction.SHORT and o.order_type is OrderType.LIMIT
    assert (o.plan.entry, o.plan.stop_loss, o.plan.take_profit) == (101.5, 103.5, 98.5)


def test_nad_poc_je_limitka_long_na_poc():
    e = SvpEngine(_cfg(), MNQ, 5)
    _day1(e)
    o = _entries(_day2(e, _ABOVE))[0]
    assert o.direction is Direction.LONG and o.order_type is OrderType.LIMIT
    assert (o.plan.entry, o.plan.stop_loss, o.plan.take_profit) == (101.5, 99.5, 104.5)


def test_smer_long_only_short_nepusti():
    e = SvpEngine(_cfg(tradeDirection="Long only"), MNQ, 5)
    _day1(e)
    assert not _entries(_day2(e, _BELOW))


def test_ciel_na_hrane_value_area():
    e = SvpEngine(_cfg(tpMode="va_edge", minRR=0.0, slPoints=1.0), MNQ, 5)
    _day1(e)
    assert _entries(_day2(e, _ABOVE))[0].plan.take_profit == 103.0      # long → VAH
    e = SvpEngine(_cfg(tpMode="va_edge", minRR=1.0, slPoints=1.0), MNQ, 5)
    _day1(e)
    assert not _entries(_day2(e, _BELOW)), "short → VAL 101 je len 0,5 bodu od POC, pod minRR"


#: pod POC, potom zavretie vysoko nad ním (prerazenie) a odchod — návrat je retest zhora
_BREAK = _BELOW + [(96, 106, 96, 105.5), (105.5, 107, 105, 106.5)]


def test_po_prerazeni_je_navrat_retest_long():
    e = SvpEngine(_cfg(tradeMode="retest"), MNQ, 5)
    _day1(e)
    outs = _day2(e, _BREAK)
    assert not _entries(outs[:4]), "pred prerazením sa v režime retest neobchoduje; bar prerazenia sa POC dotkol"
    o = _entries(outs[4:])[0]
    assert o.direction is Direction.LONG and o.plan.entry == 101.5 and "retest" in o.reason


def test_rezim_rejection_cerstve_prerazenie_neobchoduje():
    e = SvpEngine(_cfg(tradeMode="rejection"), MNQ, 5)
    _day1(e)
    outs = _day2(e, _BREAK)
    assert _entries(outs[:3]) and not _entries(outs[3:])
    assert all(o.direction is Direction.SHORT for o in _entries(outs))


def test_vstupny_model_caka_po_dotyku_na_pin_bar():
    e = SvpEngine(_cfg(entryModel="pinbar", confirmBars=3), MNQ, 5)
    _day1(e)
    touch = (96, 101.75, 96, 100.5)                 # dotyk POC zdola, nie pin bar
    pin = (100.4, 101.6, 100.2, 100.3)              # knôt hore 1,2 z rozsahu 1,4; telo 0,1
    outs = _day2(e, _BELOW + [touch, pin])
    assert not _entries(outs[:4]), "bez limitky; samotný dotyk nie je vstup"
    o = _entries(outs[4:])[0]
    assert o.direction is Direction.SHORT and o.order_type is OrderType.MARKET and o.plan.entry == 100.25


def test_vstupny_model_po_dotyku_bez_sviecky_vyprsi():
    e = SvpEngine(_cfg(entryModel="pinbar", confirmBars=2), MNQ, 5)
    _day1(e)
    plain = (100.5, 101.0, 100.0, 100.6)
    pin = (100.4, 101.6, 100.2, 100.3)
    outs = _day2(e, _BELOW + [(96, 101.75, 96, 100.5), plain, pin])
    assert not _entries(outs), "pin bar prišiel až tretí bar od dotyku"


def test_vyvijajuci_sa_poc_je_bez_aktualneho_baru():
    e = SvpEngine(_cfg(pocSource="developing"), MNQ, 5)
    _day1(e)
    assert e.profile.poc == 101.5 and e.prev is None
    outs = _day2(e, [(101.2, 101.75, 101.0, 101.5, 30)] + [r + (1,) for r in _ABOVE])
    o = _entries(outs)[0]
    assert o.direction is Direction.LONG and o.plan.entry == 101.5


def test_limitka_vyplnena_a_zavreta_v_jednom_bare_sa_rata_a_kresli():
    e = SvpEngine(_cfg(maxTradesPerDay=1), MNQ, 5)
    _day1(e)
    outs = _day2(e, _BELOW + [(96, 104, 96, 97), (97, 97.5, 95, 95.5), (95.5, 96, 95, 95.5)])   # bar 4 prešiel POC, pozícia nikdy „otvorená"
    assert [d.text for d in outs[3].drawings if d.kind.value == "svp_entry"] == ["SHORT POC"]
    assert e._trades_today == 1 and not _entries(outs[3:]), "denný strop — ďalšia limitka už nejde"
