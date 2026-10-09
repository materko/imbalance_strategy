"""Volt Break a Overnight Bias ORB: engine na syntetických baroch + priemerný ATR zo seáns.

Priemerný ATR a ADX sa v testoch enginov podstrčia (`_Val`, `_Adx`), aby sa dala skúšať logika
signálov bez skladania mesiaca dát; ATR zo seáns má vlastný test proti ručnému výpočtu Pine.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import MNQ, Bar, MarketContext, OrderAction
from tradebot.core.types import Direction
from tradebot.strategies.onbiasorb import OnBiasOrbConfig, OnBiasOrbEngine
from tradebot.strategies.voltbreak import VoltBreakConfig, VoltBreakEngine
from tradebot.strategies.voltbreak.avgatr import SessionAvgAtr

CT = ZoneInfo("America/Chicago")
FLAT = MarketContext(in_trade_window=True)


def ms(h, m, day=2):
    return int(datetime(2025, 9, day, h, m, tzinfo=CT).timestamp() * 1000)


def bar(t, o, h, lo, c, v=100.0):
    return Bar(time=t, open=o, high=h, low=lo, close=c, volume=v)


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


class _Val:
    def __init__(self, value):
        self.value = value

    def push(self, *a):
        return self.value


class _Adx:
    warmup_bars = 1

    def __init__(self, value):
        self.value = value

    def push(self, bar):
        return self.value


# ---- priemerný ATR zo seáns ---------------------------------------------- #


def test_session_atr_ako_pine():
    a = SessionAvgAtr(atr_len=2, avg_len=2)
    # tri seansy polnoc–16:00 (bar o 10:00 a 15:00), uzavreté barom o 17:00
    sessions = [(110, 100, 105), (120, 104, 118), (119, 109, 112)]
    for d, (h, lo, c) in enumerate(sessions, start=1):
        a.push(bar(ms(10, 0, d), lo, h, lo, c), 600)
        a.push(bar(ms(15, 0, d), c, c, c, c), 900)
        a.push(bar(ms(17, 0, d), c, c, c, c), 1020)          # sessDone
    # TR: 10; max(120,105)-min(104,105)=16; max(119,118)-min(109,118)=10
    # ATR: 10; 10+(16-10)/2=13; (13*1+10)/2=11.5 ; priemer posledných 2 = (13+11.5)/2
    assert a.hist[-1] == 11.5 and a.value == (13 + 11.5) / 2


# ---- Volt Break ---------------------------------------------------------- #


def volt(**kw):
    e = VoltBreakEngine(VoltBreakConfig(**kw), MNQ, 30)
    e.sess_atr = _Val(100.0)                  # Noise Up = open + 30 bodov
    return e


def test_volt_noise_a_vwap():
    e = volt()
    e.on_bar(bar(ms(0, 0), 1000, 1005, 995, 1000), ctx=FLAT)
    assert e.noise_up == 1030
    for k in range(1, 19):                    # 0:30 – 9:00, pod noise
        e.on_bar(bar(ms(k // 2, 30 * (k % 2)), 1000, 1005, 995, 1000), ctx=FLAT)
    out = e.on_bar(bar(ms(9, 30), 1000, 1050, 999, 1040), ctx=FLAT)   # zatvára sa 10:00, nad noise aj VWAP
    (intent,) = entries(out)
    assert intent.plan.direction is Direction.LONG
    assert intent.plan.take_profit == 1080 and intent.plan.stop_loss == 965    # +40 / -75 bodov (800/1500 $ NQ)


def test_volt_mimo_okna_a_pod_noise_nic():
    e = volt()
    e.on_bar(bar(ms(0, 0), 1000, 1005, 995, 1000), ctx=FLAT)
    assert not entries(e.on_bar(bar(ms(9, 0), 1000, 1050, 999, 1040), ctx=FLAT))    # zatvára sa 9:30
    assert not entries(e.on_bar(bar(ms(10, 0), 1000, 1029, 999, 1025), ctx=FLAT))   # pod noise


def test_volt_max_tri_obchody_a_casovy_exit():
    e = volt()
    e.on_bar(bar(ms(0, 0), 1000, 1005, 995, 1000), ctx=FLAT)
    n = sum(len(entries(e.on_bar(bar(ms(10, 0) + k * 1_800_000, 1040, 1050, 1035, 1045), ctx=FLAT)))
            for k in range(8))
    assert n == 3
    pos = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({"vb:1"}))
    out = e.on_bar(bar(ms(14, 0), 1045, 1046, 1044, 1045), ctx=pos)              # zatvára sa 14:30
    assert out.close_session and [o.action for o in out.orders] == [OrderAction.CLOSE]


# ---- Overnight Bias ORB -------------------------------------------------- #


def onb(open_830, adx=25.0, **kw):
    e = OnBiasOrbEngine(OnBiasOrbConfig(**kw), MNQ, 15)
    e.sess_atr = _Val(100.0)                  # SL = 30 bodov, TP = 90
    e.dmi = _Adx(adx)
    t = ms(0, 0)
    while t < ms(8, 30):                       # overnight 900..1000
        e.on_bar(bar(t, 950, 1000, 900, 950), ctx=FLAT)
        t += 900_000
    e.on_bar(bar(ms(8, 30), open_830, open_830 + 5, open_830 - 5, open_830), ctx=FLAT)
    return e


def test_onb_horna_tretina_je_long():
    e = onb(990)
    assert e.bias == 1 and (e.or_h, e.or_l) == (995, 985)
    assert not entries(e.on_bar(bar(ms(8, 45), 990, 994, 989, 993), ctx=FLAT))   # pod high rangu
    out = e.on_bar(bar(ms(9, 0), 993, 1001, 992, 1000), ctx=FLAT)
    (intent,) = entries(out)
    assert intent.plan.direction is Direction.LONG
    assert intent.plan.stop_loss == 970 and intent.plan.take_profit == 1090


def test_onb_dolna_tretina_short_stred_nic():
    e = onb(910)
    assert e.bias == -1
    (intent,) = entries(e.on_bar(bar(ms(9, 0), 905, 906, 899, 900), ctx=FLAT))
    assert intent.plan.direction is Direction.SHORT
    e = onb(950)
    assert e.bias == 0
    assert not entries(e.on_bar(bar(ms(9, 0), 950, 1100, 940, 1090), ctx=FLAT))


def test_onb_adx_jeden_obchod_a_exit():
    e = onb(990, adx=15.0)
    assert not entries(e.on_bar(bar(ms(9, 0), 993, 1001, 992, 1000), ctx=FLAT))
    e = onb(990)
    assert entries(e.on_bar(bar(ms(9, 0), 993, 1001, 992, 1000), ctx=FLAT))
    assert not entries(e.on_bar(bar(ms(9, 15), 1000, 1010, 999, 1008), ctx=FLAT))
    pos = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({"ob:1"}))
    out = e.on_bar(bar(ms(14, 15), 1000, 1001, 999, 1000), ctx=pos)               # zatvára sa 14:30
    assert out.close_session
