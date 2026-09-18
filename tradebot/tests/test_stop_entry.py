"""Stop vstup: plní sa pri prerazení úrovne, nie pri návrate k nej.

Stop je zrkadlo limitky. Limitka čaká, kým sa cena k úrovni **vráti** (long zospodu),
stop čaká, kým ju **prerazí** (long nad ňu). Pri ORB je to prirodzený vstup — prerazenie
hranice rangu je práve ten moment, na ktorý sa čaká.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.emulator import _entry_fill
from tradebot.adapters.multicharts.runner import LiveOrder
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, OrderType

T0 = 1_756_821_600_000


def bar(o, h, low, c) -> Bar:
    return Bar(time=T0, open=o, high=h, low=low, close=c, volume=1.0)


def _order(direction: Direction, entry: float, *, stop=False, market=False) -> LiveOrder:
    plan = TradePlan(direction=direction, entry=entry,
                     stop_loss=entry - 10 if direction is Direction.LONG else entry + 10,
                     take_profit=entry + 10 if direction is Direction.LONG else entry - 10,
                     qty=1.0, sl_distance=10.0)
    return LiveOrder(order_id="x", source_id=0, direction=direction, plan=plan,
                     market=market, stop=stop)


def test_ordertype_ma_stop():
    assert OrderType.STOP.value == "Stop"
    assert {t.value for t in OrderType} == {"Limit", "Market", "Stop"}


def test_stop_long_sa_plni_az_pri_prerazeni_nahor():
    o = _order(Direction.LONG, 100.0, stop=True)
    # cena sa k úrovni priblíži zdola, ale neprerazí ju — stop nesmie vstúpiť
    assert _entry_fill(bar(98.0, 99.9, 97.0, 99.0), o, first_minute=True) is None
    # prerazí — plní sa presne na úrovni
    assert _entry_fill(bar(99.0, 101.0, 98.5, 100.5), o, first_minute=False) == 100.0


def test_stop_short_sa_plni_az_pri_prerazeni_nadol():
    o = _order(Direction.SHORT, 100.0, stop=True)
    assert _entry_fill(bar(102.0, 103.0, 100.1, 101.0), o, first_minute=True) is None
    assert _entry_fill(bar(101.0, 101.5, 99.0, 99.5), o, first_minute=False) == 100.0


def test_stop_pri_medzere_plni_na_otvoreni_nie_na_urovni():
    """Keď minúta otvorí už za úrovňou, reálne sa plní na otvorení — horšie, ale pravdivo."""
    o = _order(Direction.LONG, 100.0, stop=True)
    assert _entry_fill(bar(102.0, 103.0, 101.5, 102.5), o, first_minute=False) == 102.0
    o = _order(Direction.SHORT, 100.0, stop=True)
    assert _entry_fill(bar(98.0, 98.5, 97.0, 97.5), o, first_minute=False) == 98.0


def test_stop_a_limit_sa_spravaju_zrkadlovo():
    """Limitka chce cenu POD úrovňou, stop NAD ňou — na tej istej sviečke sa líšia.

    Buy limit na 100 je pri cene 99 okamžite obchodovateľný (kupujem lacnejšie, než som
    chcel), kým buy stop na 100 pri cene 99 ešte len čaká. Nad úrovňou je to naopak.
    """
    pod_urovnou = bar(99.0, 99.5, 98.0, 98.5)      # celá sviečka pod 100
    nad_urovnou = bar(101.0, 102.0, 100.5, 101.5)  # celá sviečka nad 100

    limit_long = _order(Direction.LONG, 100.0)
    stop_long = _order(Direction.LONG, 100.0, stop=True)

    assert _entry_fill(pod_urovnou, limit_long, first_minute=False) == 99.0  # limitka: áno
    assert _entry_fill(pod_urovnou, stop_long, first_minute=False) is None   # stop: čaká
    assert _entry_fill(nad_urovnou, limit_long, first_minute=False) is None  # limitka: čaká
    assert _entry_fill(nad_urovnou, stop_long, first_minute=False) == 101.0  # stop: áno


def test_market_sa_stopom_nezmenil():
    o = _order(Direction.LONG, 100.0, market=True)
    assert _entry_fill(bar(99.0, 101.0, 98.0, 100.0), o, first_minute=True) == 99.0
    assert _entry_fill(bar(99.0, 101.0, 98.0, 100.0), o, first_minute=False) is None
