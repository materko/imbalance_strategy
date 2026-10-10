"""VALUE AREA REVERSION 1.0: profil, value area a scenár únik → slabnúci objem → návrat so silným objemom.

Testuje sa mechanika, nie edge.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction
from tradebot.strategies.varev import VaRevConfig, VaRevEngine
from tradebot.strategies.varev.engine import value_area

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]
OKNO = MarketContext(in_trade_window=True)
M15 = 900_000


def t(day: int, h: int, m: int = 0) -> int:
    return int(datetime(2025, 9, day, h, m, tzinfo=NY).timestamp() * 1000)


def test_value_area_okolo_poc():
    # objem sústredený v 100–102, okraje 90 a 110 s malým objemom
    bars = [(102.0, 100.0, 100.0)] * 8 + [(91.0, 90.0, 1.0), (110.0, 109.0, 1.0)]
    vah, val, poc = value_area(bars, 20, 70.0)
    assert 99.0 <= val <= 100.0 and 102.0 <= vah <= 103.0 and 100.0 <= poc <= 102.0
    assert value_area([], 20, 70.0) is None


def _session(e: VaRevEngine):
    """Seansa 2. 9. 18:00 → 3. 9. 18:00: obchoduje sa okolo 100–102 (VA), okraje 95 a 107."""
    ts = t(2, 18)
    bars = []
    for i in range(80):
        o, c = (100.5, 101.5) if i % 2 else (101.5, 100.5)
        bars.append(Bar(ts + i * M15, o, 102.0, 100.0, c, 100.0))
    bars.append(Bar(ts + 80 * M15, 101, 107, 101, 106, 5.0))
    bars.append(Bar(ts + 81 * M15, 106, 106, 95, 96, 5.0))
    for b in bars:
        e.on_bar(b, None, OKNO)
    return t(3, 18)


def test_unik_pod_val_slabnuci_objem_a_navrat_dava_long_s_cielom_vah():
    e = VaRevEngine(VaRevConfig(), MNQ, 15)
    ts = _session(e)
    seq = [Bar(ts, 101, 101.5, 100.6, 101, 50.0),          # nová seansa, vnútri predošlej VA
           Bar(ts + M15, 101, 101, 98, 98.5, 80.0),         # únik: zavretie pod VAL, medvedia
           Bar(ts + 2 * M15, 98.5, 99, 97, 97.5, 40.0),     # medvedia s menším objemom
           Bar(ts + 3 * M15, 97.5, 101.2, 97.4, 101, 90.0)]  # návrat dnu, býčia, objem > 40
    outs = [e.on_bar(b, None, OKNO) for b in seq]
    assert e.prev_levels is not None
    en = [o for o in outs[-1].orders if o.action is OrderAction.ENTRY]
    assert len(en) == 1 and en[0].plan.direction is Direction.LONG
    vah, val, _ = e.prev_levels
    assert en[0].plan.stop_loss == 97.0 and en[0].plan.take_profit == MNQ.round_price(vah)
    assert not any(o.orders for o in outs[:-1])


def test_bez_poklesu_objemu_signal_nie_je():
    e = VaRevEngine(VaRevConfig(), MNQ, 15)
    ts = _session(e)
    seq = [Bar(ts, 101, 101.5, 100.6, 101, 50.0), Bar(ts + M15, 101, 101, 98, 98.5, 40.0),
           Bar(ts + 2 * M15, 98.5, 99, 97, 97.5, 80.0), Bar(ts + 3 * M15, 97.5, 101.2, 97.4, 101, 90.0)]
    assert not any(e.on_bar(b, None, OKNO).orders for b in seq)


def test_navrat_neskoro_signal_nie_je():
    e = VaRevEngine(VaRevConfig(maxBarsOutside=2), MNQ, 15)
    ts = _session(e)
    seq = [Bar(ts, 101, 101.5, 100.6, 101, 50.0), Bar(ts + M15, 101, 101, 98, 98.5, 80.0),
           Bar(ts + 2 * M15, 98.5, 99, 97, 97.5, 40.0), Bar(ts + 3 * M15, 97.5, 98, 97.2, 97.6, 30.0),
           Bar(ts + 4 * M15, 97.6, 101.2, 97.4, 101, 90.0)]
    assert not any(e.on_bar(b, None, OKNO).orders for b in seq)


def test_predhistoria_da_rovnaky_profil():
    a, b = VaRevEngine(VaRevConfig(), MNQ, 15), VaRevEngine(VaRevConfig(), MNQ, 15)
    bars = []
    ts = t(2, 18)
    for i in range(100):
        bars.append(Bar(ts + i * M15, 100 + i % 3, 102 + i % 5, 99 - i % 4, 101, 10.0 + i))
    for x in bars:
        a.on_bar(x, None, OKNO)
    b._seed(bars, None)
    assert a.prev_levels == b.prev_levels and a.levels == b.levels


def test_value_area_len_z_ny_seansy_predosleho_dna():
    """Profil NY: bary mimo 9:30–16:00 do neho nejdú; po 16:00 platí ako previous na ďalší deň."""
    from tradebot.strategies.varev import ProfileSession

    e = VaRevEngine(VaRevConfig(profileSession=ProfileSession.NY), MNQ, 15)
    ts = t(2, 4)
    bars = [Bar(ts + i * M15, 150, 160, 140, 150, 1000.0) for i in range(22)]       # 4:00–9:30 mimo NY, veľký objem
    ts = t(2, 9, 30)
    bars += [Bar(ts + i * M15, 101, 102, 100, 101, 100.0) for i in range(26)]       # NY 9:30–16:00 okolo 100–102
    bars.append(Bar(t(2, 16), 101, 102, 100, 101, 10.0))                            # prvý bar po NY → profil hotový
    for b in bars:
        e.on_bar(b, None, OKNO)
    vah, val, poc = e.prev_levels
    assert 100.0 <= val < vah <= 102.0 and e.levels == e.prev_levels


def test_ny_profil_v_predhistorii_rovnaky():
    from tradebot.strategies.varev import ProfileSession

    c = VaRevConfig(profileSession=ProfileSession.NY)
    a, b = VaRevEngine(c, MNQ, 15), VaRevEngine(c, MNQ, 15)
    ts = t(2, 4)
    bars = [Bar(ts + i * M15, 100 + i % 3, 102 + i % 5, 99 - i % 4, 101, 10.0 + i) for i in range(150)]
    for x in bars:
        a.on_bar(x, None, OKNO)
    b._seed(bars, None)
    assert a.prev_levels == b.prev_levels and a.prev_levels is not None
