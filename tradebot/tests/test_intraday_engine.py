"""INTRADAY 1.0: engine na syntetických baroch MNQ.

Testuje sa mechanika, nie edge: SD zóna (báza + impulz + odchod, bez pohľadu dopredu), daily bias, PDH/PDL
a zobratie likvidity, vnorenie zón a limitka na proximal v NY okne.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType, SizeSpec
from tradebot.strategies.intraday import BiasMode, IntradayConfig, IntradayEngine, LiqMode
from tradebot.strategies.intraday.engine import _Zone, _ZoneFinder

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]
OKNO = MarketContext(in_trade_window=True)
H = 3_600_000


def t(day: int, h: int, m: int = 0) -> int:
    """Čas New York, september 2025 (1. 9. je pondelok)."""
    return int(datetime(2025, 9, day, h, m, tzinfo=NY).timestamp() * 1000)


def B(ts: int, o: float, h: float, l: float, c: float) -> Bar:
    return Bar(ts, o, h, l, c, 100.0)


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


def cfg(**kw) -> IntradayConfig:
    base = dict(atrLen=3, impulseMinBodyAtr=SizeSpec(0.5, "atr"), legOutMinAtr=SizeSpec(1.0, "atr"))
    base.update(kw)
    return IntradayConfig(**base)


def finder_bars():
    """Pohyb (veľké telá — nie báza), báza 2 malé sviečky 99–104, impulz hore, odchod zavretím 125."""
    bars = [B(t(2, 2 + i), 96, 105, 95, 104) for i in range(4)]
    bars += [B(t(2, 6), 101, 104, 99, 102), B(t(2, 7), 102, 104, 100, 101)]     # báza: telá 1 b. pri rozsahu 4–5
    bars += [B(t(2, 8), 102, 115, 101, 114)]                                      # impulz
    bars += [B(t(2, 9), 114, 126, 113, 125)]                                      # odchod dokončený zavretím
    return bars


def test_zona_vznikne_az_na_bare_odchodu_s_proximal_na_tele_a_distal_na_knote():
    f = _ZoneFinder(60, cfg(), MNQ)
    uid = iter(range(1, 100)).__next__
    born = [(b.time, f.push(b, uid)) for b in finder_bars()]
    nove = [(ts, z) for ts, zs in born for z in zs]
    assert len(nove) == 1
    ts, z = nove[0]
    assert ts == t(2, 9)                                   # nie na impulze, až keď odchod dobehol
    assert z.direction is Direction.LONG and z.top == 102 and z.bottom == 99
    assert z.born_ms == t(2, 10)                           # zavretie baru odchodu


def test_slaby_odchod_zonu_nevytvori():
    f = _ZoneFinder(60, cfg(legOutMinAtr=SizeSpec(5.0, "atr")), MNQ)
    uid = iter(range(1, 100)).__next__
    assert not [z for b in finder_bars() for z in f.push(b, uid)]


def _rth_day(e: IntradayEngine, day: int, lo: float, hi: float, close: float) -> None:
    """RTH deň na 60m baroch: 9:00–16:00 (bar končiaci 10:00 … 16:00), low/high/zavretie."""
    for h in range(9, 16):
        c = close if h == 15 else (lo + hi) / 2
        e.on_bar(B(t(day, h), c, hi if h == 12 else c + 1, lo if h == 10 else c - 1, c), None, OKNO)


def test_pdh_pdl_bias_a_zobratie_likvidity():
    e = IntradayEngine(cfg(biasMode=BiasMode.CLOSE2, liqMode=LiqMode.SWEEP, entryTF=60), MNQ, 60)
    _rth_day(e, 1, 90.0, 130.0, 100.0)
    _rth_day(e, 2, 95.0, 120.0, 110.0)
    e.on_bar(B(t(2, 17), 110, 111, 109, 110), None, OKNO)           # po 16:00 → deň 2 uzavretý
    assert (e.pdh, e.pdl) == (120.0, 95.0)
    assert e.bias is Direction.LONG                                   # 110 > 100
    e.on_bar(B(t(2, 18), 110, 111, 109, 110), None, OKNO)           # Globex 3. 9. od 18:00
    assert not e._liq_ok(Direction.LONG)
    e.on_bar(B(t(2, 19), 110, 111, 94, 100), None, OKNO)            # low 94 < PDL 95
    assert e._liq_ok(Direction.LONG) and not e._liq_ok(Direction.SHORT)


def test_vnorenie_podla_polohy_nie_poradia():
    e = IntradayEngine(cfg(entryTF=15), MNQ, 5)
    parent = _Zone(60, Direction.LONG, 110.0, 100.0, t(2, 6), t(2, 9), t(3, 9), 1)
    inside = _Zone(15, Direction.LONG, 106.0, 103.0, t(2, 6), t(2, 7), t(3, 7), 2)    # vznikla skôr ako 1H
    outside = _Zone(15, Direction.LONG, 130.0, 125.0, t(2, 8), t(2, 9), t(3, 9), 3)
    for z in (parent, inside, outside):
        e._add_zone(z, None)
    assert e._chain(inside) == [parent] and e._chain(outside) is None
    parent.alive = False
    assert e._chain(inside) is None


def test_limitka_na_proximal_v_ny_okne():
    """1H zóna (graf 60m) v smere biasu, cena nad ňou v okne → limitka na hornú hranu zóny."""
    c = cfg(biasMode=BiasMode.OFF, liqMode=LiqMode.OFF, entryTF=60)
    e = IntradayEngine(c, MNQ, 60)
    outs = []
    bars = [B(t(2, 4 + i), 96, 105, 95, 104) for i in range(2)]
    bars += [B(t(2, 6), 101, 104, 99, 102), B(t(2, 7), 102, 104, 100, 101), B(t(2, 8), 102, 115, 101, 114),
             B(t(2, 9), 114, 126, 113, 125)]                       # zóna 99–102 vznikne o 10:00
    for b in bars:
        outs.append(e.on_bar(b, None, OKNO))
    out = e.on_bar(B(t(2, 10), 125, 127, 120, 122), None, OKNO)    # bar končiaci 11:00, v okne
    en = entries(out)
    assert en and en[0].order_type is OrderType.LIMIT and en[0].plan.entry == 102.0
    assert en[0].plan.stop_loss < 99.0 and en[0].plan.direction is Direction.LONG
    assert not any(entries(o) for o in outs[:4])                   # pred vznikom zóny nič


def test_mimo_okna_sa_nevstupuje():
    c = cfg(biasMode=BiasMode.OFF, liqMode=LiqMode.OFF, entryTF=60)
    e = IntradayEngine(c, MNQ, 60)
    bars = [B(t(2, 0 + i), 96, 105, 95, 104) for i in range(2)]
    bars += [B(t(2, 2), 101, 104, 99, 102), B(t(2, 3), 102, 104, 100, 101), B(t(2, 4), 102, 115, 101, 114),
             B(t(2, 5), 114, 126, 113, 125), B(t(2, 6), 125, 127, 120, 122)]   # všetko pred 9:30
    assert not any(entries(e.on_bar(b, None, OKNO)) for b in bars)


def test_predhistoria_da_rovnaky_stav():
    c = cfg(biasMode=BiasMode.CLOSE2, entryTF=60)
    a = IntradayEngine(c, MNQ, 60)
    b = IntradayEngine(c, MNQ, 60)
    bars = []
    for day, (lo, hi, cl) in ((1, (90.0, 130.0, 100.0)), (2, (95.0, 120.0, 110.0))):
        for h in range(9, 16):
            x = cl if h == 15 else (lo + hi) / 2
            bars.append(B(t(day, h), x, hi if h == 12 else x + 1, lo if h == 10 else x - 1, x))
    for x in bars:
        a.on_bar(x, None, OKNO)
    b._seed(bars, None)
    assert (a.pdh, a.pdl, a.closes, a.bias) == (b.pdh, b.pdl, b.closes, b.bias)


def test_likvidita_zona_pri_pdl():
    e = IntradayEngine(cfg(entryTF=60, liqTolAtr=SizeSpec(0.0, "atr")), MNQ, 60)
    e.pdl, e.pdh = 100.0, 120.0
    low = _Zone(60, Direction.LONG, 99.0, 95.0, 0, 0, 0, 1)
    high = _Zone(60, Direction.LONG, 110.0, 105.0, 0, 0, 0, 2)
    assert e._liq_ok(Direction.LONG, low) and not e._liq_ok(Direction.LONG, high)
