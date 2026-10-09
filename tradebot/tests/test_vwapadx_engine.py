"""VWAP ADX: engine na syntetických 1m baroch.

ADX sa v testoch podstrčí (`_Adx`), aby sa dala skúšať postupnosť krokov bez skladania trhu,
ktorý by dal presne požadovaný ADX. Výpočet ADX samotný je IBS `DMI` a má vlastné testy.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import MNQ, Bar, MarketContext, OrderAction
from tradebot.core.types import Direction
from tradebot.strategies.vwapadx import VwapAdxConfig, VwapAdxEngine

CT = ZoneInfo("America/Chicago")
MIN = 60_000
FLAT = MarketContext(in_trade_window=True)


def ms(h, m, day=2):
    return int(datetime(2025, 9, day, h, m, tzinfo=CT).timestamp() * 1000)


class _Adx:
    """Podstrčený DMI: vracia hodnoty zo zoznamu (posledná sa opakuje)."""

    warmup_bars = 1

    def __init__(self, values):
        self.values = list(values)

    def push(self, bar):
        return self.values.pop(0) if len(self.values) > 1 else self.values[0]


def bar(t, o, h, lo, c, v=100.0):
    return Bar(time=t, open=o, high=h, low=lo, close=c, volume=v)


def engine(adx=(30.0,), **kw):
    e = VwapAdxEngine(VwapAdxConfig(**kw), MNQ, 1)
    e.dmi = _Adx(adx)
    return e


def opening_range(e, lo=100.0, hi=110.0):
    """8:30–8:59: range lo..hi, close v strede."""
    for k in range(30):
        e.on_bar(bar(ms(8, 30 + k), 105, hi, lo, 105), ctx=FLAT)


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


# --------------------------------------------------------------------------- #


def test_defaulty_ako_pine():
    cfg = VwapAdxConfig()
    assert (cfg.orStartHHMM, cfg.orEndHHMM, cfg.exitHHMM) == (830, 900, 1555)
    assert cfg.vwapAnchor.value == "RTH 8:30 CT" and cfg.adxMin == 20.0
    assert (cfg.tpBars, cfg.slBars, cfg.maxTrades) == (5, 20, 1)


def test_opening_range_a_vwap_od_830():
    e = engine()
    e.on_bar(bar(ms(8, 29), 50, 60, 40, 50), ctx=FLAT)      # pred rangom, do VWAP od 8:30 nejde
    e.on_bar(bar(ms(8, 30), 100, 110, 90, 105), ctx=FLAT)
    assert (e.or_h, e.or_l) == (110, 90)
    assert abs(e.vwap.value - (110 + 90 + 105) / 3) < 1e-9
    e.on_bar(bar(ms(8, 31), 105, 120, 95, 110), ctx=FLAT)
    assert (e.or_h, e.or_l) == (120, 90)
    e.on_bar(bar(ms(9, 0), 110, 130, 80, 110), ctx=FLAT)    # 9:00 už do rangu nepatrí
    assert (e.or_h, e.or_l) == (120, 90)


def test_prerazenie_dotyk_a_zavretie_nad_vwap_je_long():
    e = engine()
    opening_range(e)
    out = e.on_bar(bar(ms(9, 0), 108, 114, 107, 113), ctx=FLAT)   # zavretie nad high rangu -> nabitá
    assert e.armed and not e.touched and not entries(out)
    vw = e.vwap.value
    out = e.on_bar(bar(ms(9, 1), 112, 113, vw - 0.5, vw + 1), ctx=FLAT)   # dotyk VWAP a zavretie nad ním
    (intent,) = entries(out)
    plan = intent.plan
    assert intent.plan.direction is Direction.LONG and intent.order_type.value == "Market"
    assert plan.take_profit == MNQ.round_price(114)          # najvyšší high posledných 5 barov
    assert plan.stop_loss == MNQ.round_price(100)            # najnižší low posledných 20 barov (range)
    assert not e.touched                                     # ďalší vstup potrebuje nový dotyk


def test_kroky_v_jednej_sviecke():
    e = engine()
    opening_range(e)
    vw = e.vwap.value
    out = e.on_bar(bar(ms(9, 0), 105, 115, vw - 1, 112), ctx=FLAT)   # nad range, dotkne sa VWAP, zavrie nad
    assert len(entries(out)) == 1


def test_bez_prerazenia_rangu_nic():
    e = engine()
    opening_range(e)
    vw = e.vwap.value
    out = e.on_bar(bar(ms(9, 0), 105, 109, vw - 1, 108), ctx=FLAT)   # pod high rangu
    assert not e.armed and not entries(out)


def test_adx_musi_byt_nad_prahom_a_nerast():
    # 31 barov rangu (vrátane 8:29 nie) + bar prerazenia: ADX stúpa -> čaká; potom klesne -> vstup
    vals = [30.0] * 30 + [31.0, 32.0, 31.5]
    e = engine(adx=vals)
    opening_range(e)
    vw = e.vwap.value
    out = e.on_bar(bar(ms(9, 0), 105, 115, vw - 1, 112), ctx=FLAT)    # ADX 31 > 30 -> stúpa
    assert e.armed and e.touched and not entries(out)
    out = e.on_bar(bar(ms(9, 1), 112, 114, 111, 113), ctx=FLAT)       # ADX 32 > 31 -> stúpa
    assert not entries(out)
    out = e.on_bar(bar(ms(9, 2), 113, 114, 112, 113), ctx=FLAT)       # ADX 31.5 <= 32 -> vstup
    assert len(entries(out)) == 1

    e = engine(adx=(15.0,))                                            # pod prahom 20
    opening_range(e)
    assert not entries(e.on_bar(bar(ms(9, 0), 105, 115, e.vwap.value - 1, 112), ctx=FLAT))


def test_max_jeden_obchod_denne():
    e = engine()
    opening_range(e)
    vw = e.vwap.value
    assert entries(e.on_bar(bar(ms(9, 0), 105, 115, vw - 1, 112), ctx=FLAT))
    vw = e.vwap.value
    assert not entries(e.on_bar(bar(ms(9, 5), 112, 115, vw - 1, 112), ctx=FLAT))


def test_casovy_exit_1555():
    e = engine()
    opening_range(e)
    pos = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({"va:1"}))
    out = e.on_bar(bar(ms(15, 53), 100, 101, 99, 100), ctx=pos)      # zatvára sa 15:54
    assert not out.close_session
    out = e.on_bar(bar(ms(15, 54), 100, 101, 99, 100), ctx=pos)      # zatvára sa 15:55
    assert out.close_session and [o.action for o in out.orders] == [OrderAction.CLOSE]


def test_po_casovom_exite_uz_ziadny_signal():
    e = engine()
    opening_range(e)
    vw = e.vwap.value
    assert not entries(e.on_bar(bar(ms(15, 54), 105, 115, vw - 1, 112), ctx=FLAT))
