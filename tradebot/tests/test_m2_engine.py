"""METODA 2 (M2) 1.0: engine na syntetických 1m baroch.

Testuje sa pravidlo z podkladu: negatívna sviečka = zavretie pod 50 % rozsahu (aj zelená), potvrdenie celým
telom nad ňou, limitka na high M2, stop pod low M2, cieľ RR; short zrkadlovo; telo, ktoré nie je celé nad M2,
nepotvrdzuje; zavretie za stopom setup zruší; filter EMA blokuje protismer.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.m2 import M2Config, M2Engine

NY = ZoneInfo("America/New_York")
ES = INSTRUMENTS["es_databento"]
M1 = 60_000
FLAT = MarketContext(in_trade_window=True)
T0 = int(datetime(2025, 9, 3, 10, 0, tzinfo=NY).timestamp() * 1000)


def eng(**kw) -> M2Engine:
    return M2Engine(M2Config(**{"useEmaTrend": False, **kw}), ES, 1)


def feed(e: M2Engine, bars):
    """bars = (open, high, low, close)"""
    return [e.on_bar(Bar(T0 + i * M1, o, h, l, c, 100.0), None, FLAT) for i, (o, h, l, c) in enumerate(bars)]


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


def test_long_m2_potvrdena_celym_telom_dava_limit_na_high():
    outs = feed(eng(), [
        (5000.00, 5001.00, 4998.00, 4998.50),   # negatívna (close pod 50 %) = M2
        (4998.75, 5001.50, 4998.50, 5001.25),   # pozitívna, telo nie je celé nad 5001
        (5001.25, 5003.00, 5001.25, 5002.75),   # telo 5001.25–5002.75 celé nad high M2 5001 → potvrdenie
    ])
    assert not entries(outs[1])
    o = entries(outs[2])[0]
    assert o.order_type is OrderType.LIMIT and o.direction is Direction.LONG
    assert o.plan.entry == 5001.00
    assert o.plan.stop_loss == 4998.00 - ES.tick_size
    assert o.plan.take_profit == ES.round_price(5001.00 + 2.0 * (5001.00 - o.plan.stop_loss))


def test_zelena_sviecka_so_zavretim_pod_polovicou_je_negativna():
    outs = feed(eng(), [
        (4998.00, 5002.00, 4997.00, 4999.00),   # zelená (close > open), ale close pod 50 % (4999.5) → M2
        (5002.25, 5004.00, 5002.00, 5003.50),   # telo celé nad 5002 → potvrdenie
    ])
    assert entries(outs[1])[0].plan.entry == 5002.00


def test_short_zrkadlovo_z_poslednej_pozitivnej():
    outs = feed(eng(), [
        (5000.00, 5002.00, 4999.00, 5001.75),   # pozitívna = M2 short
        (4998.50, 4998.75, 4996.00, 4996.50),   # telo celé pod low 4999 → potvrdenie
    ])
    o = entries(outs[1])[0]
    assert o.direction is Direction.SHORT and o.plan.entry == 4999.00
    assert o.plan.stop_loss == 5002.00 + ES.tick_size


def test_zavretie_za_stopom_zrusi_setup():
    e = eng()
    feed(e, [(5000.00, 5001.00, 4998.00, 4998.50), (5001.25, 5003.00, 5001.25, 5002.75)])
    out = e.on_bar(Bar(T0 + 2 * M1, 5002.00, 5002.25, 4995.00, 4995.50, 100.0), None, FLAT)   # zavrie pod stopom
    assert [o.action for o in out.orders][:1] == [OrderAction.CANCEL]


def test_filter_ema_blokuje_long_v_downtrende():
    e = M2Engine(M2Config(ema1=2, ema2=3, ema3=4, ema4=5, ema5=6), ES, 1)
    down = [(5100 - 5 * i, 5101 - 5 * i, 5098 - 5 * i, 5099 - 5 * i) for i in range(10)]
    outs = feed(e, down + [(5050.00, 5051.00, 5048.00, 5048.50), (5051.25, 5053.00, 5051.25, 5052.75)])
    assert not entries(outs[-1])
