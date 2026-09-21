"""ORB + EMA: štyri nezávislé roly jedného priemeru.

EMA v ORB vie robiť štyri veci a každá má vlastný prepínač: filtrovať smer prerazenia
(`emaFilter`), vybrať dni podľa toho, kde vznikol opening range (`emaRangeFilter`),
zavrieť pozíciu pri návrate cez priemer (`emaExit`) a len sa kresliť (`showEma`).
Testuje sa, že každá robí presne svoje a že vypnutá EMA nemení nič — ani rozbeh.

Ceny sú okolo 100, opening range je 100,0–101,0 (šírka 1 %, prejde filtrami šírky).
Kde má byť EMA, sa riadi cenou predhistórie: nižšia predhistória = EMA pod rangom.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tradebot.core import BTCUSDT_BINANCE, Bar, MarketContext, OrderAction
from tradebot.core.ma import EMA
from tradebot.core.types import Direction
from tradebot.strategies.orb import ORBConfig, ORBEngine, SessionMode
from tradebot.strategies.orb.config import EntryMode

NY = ZoneInfo("America/New_York")
#: utorok 2025-09-02, 9:30 New York — `weekdaysOnly` je zapnutý, víkend by testy vypol
OPEN_MS = int(datetime(2025, 9, 2, 9, 30, tzinfo=NY).timestamp() * 1000)
MIN = 60_000
OKNO = MarketContext(in_trade_window=True)
RANGE_HI, RANGE_LO = 101.0, 100.0
STRED = (RANGE_HI + RANGE_LO) / 2.0
EMA_LEN = 20


def bar(ts: int, o=100.0, h=100.2, low=99.8, c=100.0, v=10.0) -> Bar:
    return Bar(time=ts, open=o, high=h, low=low, close=c, volume=v)


def _engine(**kw) -> ORBEngine:
    kw.setdefault("emaLen", EMA_LEN)
    cfg = ORBConfig(sessionMode=SessionMode.NY, nyRangeMinutes=5, entryMode=EntryMode.CLOSE,
                    minClosePosPct=0, showRange=False, showLevels=False, **kw)
    return ORBEngine(cfg, BTCUSDT_BINANCE, 1)


def _warm(engine: ORBEngine, price: float) -> None:
    """Predhistória na danej cene — určuje, kde bude EMA, keď sa seansa otvorí."""
    for i in range(engine.required_history, 0, -1):
        engine.on_bar(bar(OPEN_MS - i * MIN, o=price, h=price + 0.1, low=price - 0.1, c=price),
                      None, OKNO)


def _session(engine: ORBEngine, break_close: float):
    """Päť barov opening rangu a na šiestom prerazenie so zadaným zavretím."""
    for n in range(5):
        engine.on_bar(bar(OPEN_MS + n * MIN, o=STRED, h=RANGE_HI, low=RANGE_LO, c=STRED), None, OKNO)
    b = bar(OPEN_MS + 5 * MIN, o=STRED, h=max(RANGE_HI, break_close),
            low=min(RANGE_LO, break_close), c=break_close)
    return engine.on_bar(b, None, OKNO)


def _entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


def _run(break_close: float, warm_price: float, **kw):
    engine = _engine(**kw)
    _warm(engine, warm_price)
    return _entries(_session(engine, break_close))


# ---- vypnutá EMA nemení nič ------------------------------------------- #


def test_vypnuta_ema_nepredlzuje_rozbeh_ani_nekresli():
    base = ORBEngine(ORBConfig(), BTCUSDT_BINANCE, 3)
    s_emou = ORBEngine(ORBConfig(emaLen=200), BTCUSDT_BINANCE, 3)
    assert s_emou.required_history == base.required_history == 50


@pytest.mark.parametrize("smer,close", [("long", RANGE_HI + 0.5), ("short", RANGE_LO - 0.5)])
def test_bez_ema_prejde_prerazenie_na_obe_strany(smer, close):
    assert len(_run(close, warm_price=100.5)) == 1


# ---- filter smeru prerazenia ------------------------------------------- #


def test_filter_pusti_long_len_nad_ema():
    """EMA hlboko pod rangom: long prejde, short nie — hoci prerazí hranicu."""
    assert len(_run(RANGE_HI + 0.5, warm_price=95.0, emaFilter=True)) == 1
    assert _run(RANGE_LO - 0.5, warm_price=95.0, emaFilter=True) == []


def test_filter_pusti_short_len_pod_ema():
    assert len(_run(RANGE_LO - 0.5, warm_price=110.0, emaFilter=True)) == 1
    assert _run(RANGE_HI + 0.5, warm_price=110.0, emaFilter=True) == []


def test_filter_bez_rozbehnutej_ema_neobchoduje():
    """Kým EMA nemá dosť barov, filter sa nedá vyhodnotiť — vtedy sa nevstupuje."""
    engine = _engine(emaFilter=True)
    # zámerne menej barov, než EMA potrebuje na rozbeh (seansa pridá ďalších 6)
    for i in range(EMA_LEN - 14, 0, -1):
        engine.on_bar(bar(OPEN_MS - i * MIN, o=95.0, h=95.1, low=94.9, c=95.0), None, OKNO)
    assert _entries(_session(engine, RANGE_HI + 0.5)) == []


def test_filter_predlzi_rozbeh_o_ema():
    from tradebot.core.warmup import ema_bars

    engine = _engine(emaFilter=True, emaLen=200)
    assert engine.required_history == ema_bars(200) == 500


# ---- filter dňa podľa rangu -------------------------------------------- #


def test_range_nad_ema_pusti_len_longy():
    assert len(_run(RANGE_HI + 0.5, warm_price=95.0, emaRangeFilter=True)) == 1
    assert _run(RANGE_LO - 0.5, warm_price=95.0, emaRangeFilter=True) == []


def test_range_pod_ema_pusti_len_shorty():
    assert len(_run(RANGE_LO - 0.5, warm_price=110.0, emaRangeFilter=True)) == 1
    assert _run(RANGE_HI + 0.5, warm_price=110.0, emaRangeFilter=True) == []


def test_ema_vnutri_rangu_zahodi_cely_den():
    """Ani long, ani short — trh sa otvoril presne na priemere, deň nemá smer."""
    assert _run(RANGE_HI + 0.5, warm_price=STRED, emaRangeFilter=True) == []
    assert _run(RANGE_LO - 0.5, warm_price=STRED, emaRangeFilter=True) == []


def test_oba_filtre_naraz_sa_neblokuju():
    assert len(_run(RANGE_HI + 0.5, warm_price=95.0, emaFilter=True, emaRangeFilter=True)) == 1


# ---- výstup cez EMA ---------------------------------------------------- #


def _exit_out(close: float, position: float, warm_price: float = 100.0):
    engine = _engine(emaExit=True)
    _warm(engine, warm_price)
    ctx = MarketContext(in_trade_window=True, position_size=position,
                        open_order_ids=frozenset({"orb:ny:1"}))
    return engine.on_bar(bar(OPEN_MS, o=close, h=close + 0.1, low=close - 0.1, c=close), None, ctx)


def test_long_sa_zavrie_pri_zavreti_pod_ema():
    out = _exit_out(close=95.0, position=1.0)
    assert out.close_session is True
    closes = [o for o in out.orders if o.action is OrderAction.CLOSE]
    assert [o.order_id for o in closes] == ["orb:ny:1"]
    assert "EMA" in closes[0].reason


def test_short_sa_zavrie_pri_zavreti_nad_ema():
    out = _exit_out(close=105.0, position=-1.0)
    assert out.close_session is True


def test_pozicia_na_spravnej_strane_ema_sa_nezavrie():
    assert _exit_out(close=105.0, position=1.0).close_session is False
    assert _exit_out(close=95.0, position=-1.0).close_session is False


def test_bez_pozicie_sa_nic_nezavrie():
    assert _exit_out(close=95.0, position=0.0).close_session is False


# ---- kreslenie --------------------------------------------------------- #


def test_show_ema_kresli_ciaru_a_nepredlzuje_rozbeh():
    engine = _engine(showEma=True)
    assert engine.required_history == 50, "kreslenie nesmie odkladať prvý obchod"
    _warm(engine, 100.0)
    out = _session(engine, RANGE_HI + 0.5)
    ciary = [d for d in out.drawings if d.kind.value == "orb_ema"]
    assert len(ciary) == 1 and ciary[0].y2 == pytest.approx(engine._ema.value)


def test_bez_show_ema_sa_nekresli_nic():
    engine = _engine(emaFilter=True)
    _warm(engine, 95.0)
    out = _session(engine, RANGE_HI + 0.5)
    assert [d for d in out.drawings if d.kind.value == "orb_ema"] == []


# ---- samotná hodnota --------------------------------------------------- #


def test_ema_enginu_sedi_s_referenciou_z_jadra():
    engine = _engine(showEma=True)
    ref = EMA(EMA_LEN)
    closes = []
    for i in range(engine.required_history, 0, -1):
        c = 100.0 + i * 0.01
        closes.append(c)
        engine.on_bar(bar(OPEN_MS - i * MIN, o=c, h=c + 0.1, low=c - 0.1, c=c), None, OKNO)
    for c in closes:
        ref.push(c)
    assert engine._ema.value == pytest.approx(ref.value)


def test_strana_rangu_sa_zapamata_na_den():
    engine = _engine(emaRangeFilter=True)
    _warm(engine, 95.0)
    _session(engine, RANGE_HI + 0.5)
    assert engine._state["ny"].ema_side is Direction.LONG
