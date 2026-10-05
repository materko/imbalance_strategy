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


# ---- Fibonacci ako konfluencia s POC ---------------------------------------- #

def test_noha_swing_dno_vrchol_a_jej_urovne():
    from tradebot.strategies.fibo.legs import SwingLegs
    legs = SwingLegs(5, 5, 2, 3, 0.0)
    rows = [(103, 104, 102, 103), (103, 103.5, 101, 101.5), (101.5, 102, 100, 101), (101, 104, 100.8, 103.5),
            (103.5, 107, 103, 106.5), (106.5, 110, 106, 109.5), (109.5, 109.8, 107, 107.5), (107.5, 108, 105, 105.5)]
    for i, r in enumerate(rows):
        legs.on_bar(_bar(_t(3, 9, 30) + i * MIN5, *r))
    # swing bar sa zavrie až s ďalším barom grafu → ešte jeden bar
    legs.on_bar(_bar(_t(3, 9, 30) + 8 * MIN5, 105.5, 106, 105.2, 105.8))
    leg = legs.legs[Direction.LONG]
    assert (leg.start, leg.end) == (100, 110) and leg.level(0.5) == 105 and leg.level(-0.27) == 112.7
    assert abs(leg.retrace(103.82) - 0.618) < 1e-9
    legs.on_bar(_bar(_t(3, 9, 30) + 9 * MIN5, 105.8, 111, 105.5, 110.5))
    assert legs.legs[Direction.LONG].end == 111, "noha pokračuje — koniec sa posúva"
    legs.on_bar(_bar(_t(3, 9, 30) + 10 * MIN5, 110.5, 110.6, 99.5, 100))
    assert Direction.LONG not in legs.legs, "100 % prerazené"


#: deň 2: noha 98 → 108 cez POC 101,5 (POC = 65 % návratu)
def _up_leg(lo: float, hi: float):
    return [(lo + 2, lo + 3, lo + 1.5, lo + 2), (lo + 2, lo + 2.5, lo + 1, lo + 1.2), (lo + 1.2, lo + 1.5, lo, lo + 1),
            (lo + 1, lo + 4, lo + 0.8, lo + 3.5), (lo + 3.5, hi - 2, lo + 3, hi - 2.5), (hi - 2.5, hi, hi - 3, hi - 0.5),
            (hi - 0.5, hi - 0.2, hi - 1.5, hi - 1), (hi - 1, hi - 0.6, hi - 1.6, hi - 1.2), (hi - 1.2, hi - 0.8, hi - 1.8, hi - 1.4)]


def _fib_cfg(**kw):
    base = dict(useFibo=True, fibSwingTF=5, fibSwingLen=2, fibLegMinAtr=0.0, fibMinPct=38.2, fibMaxPct=78.6,
                awayAtr=0.5, tradeDirection="Long only", tradeStartH=0, tradeStartM=0, tradeEndH=23, tradeEndM=59)
    base.update(kw)
    return _cfg(**base)


def test_fibo_poc_v_pasme_navratu_nohy_sa_obchoduje():
    e = SvpEngine(_fib_cfg(), MNQ, 5)
    _day1(e)
    outs = _day2(e, _up_leg(98, 108))
    leg = e.legs.legs[Direction.LONG]
    assert (leg.start, leg.end) == (98, 108) and abs(leg.retrace(101.5) - 0.65) < 1e-9
    o = _entries(outs)[-1]
    assert o.direction is Direction.LONG and o.plan.entry == 101.5
    assert not _entries(outs[:7]), "kým noha nie je potvrdená (2 bary za vrcholom), POC sa neobchoduje"


def test_fibo_poc_mimo_pasma_sa_neobchoduje():
    e = SvpEngine(_fib_cfg(fibMinPct=10.0, fibMaxPct=30.0), MNQ, 5)
    _day1(e)
    outs = _day2(e, _up_leg(98, 108))
    leg = e.legs.legs[Direction.LONG]
    assert (leg.start, leg.end) == (98, 108), "tá istá noha, POC na 65 % — mimo pásma 10–30 %"
    assert not _entries(outs)


def test_fibo_stop_za_nohu_a_ciel_na_extenzii():
    e = SvpEngine(_fib_cfg(slMode="leg", slBufferAtr=0.0, tpMode="extension", tpExtensionPct=27.0, minRR=0.0), MNQ, 5)
    _day1(e)
    o = _entries(_day2(e, _up_leg(98, 108)))[-1]
    assert (o.plan.entry, o.plan.stop_loss) == (101.5, 98.0) and abs(o.plan.take_profit - 110.7) < 0.26


def test_fibo_vypnute_nic_nemeni():
    a, b = SvpEngine(_cfg(), MNQ, 5), SvpEngine(_cfg(useFibo=False, fibMinPct=1, fibMaxPct=2), MNQ, 5)
    _day1(a); _day1(b)
    oa, ob = _entries(_day2(a, _ABOVE)), _entries(_day2(b, _ABOVE))
    assert b.legs is None and [(o.plan.entry, o.plan.stop_loss) for o in oa] == [(o.plan.entry, o.plan.stop_loss) for o in ob]


def test_fibo_stop_za_nohu_bez_filtra_config_odmietne():
    import pytest
    with pytest.raises(Exception):
        SvpConfig(slMode="leg").validate()
