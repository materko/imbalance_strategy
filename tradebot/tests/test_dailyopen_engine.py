"""DAILY OPEN 1.0: engine na syntetických 60m baroch.

Testuje sa mechanika podľa videa: úroveň zo zavretia polnoci, stop order od 8:00 na úrovni + 30 bodov,
vstup na zavretí (variant), podmienka prierazu v noci, zrušenie nevyplneného orderu na konci okna,
výstup o 16:00 a short pri oboch smeroch.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.dailyopen import BreakMode, DailyOpenConfig, DailyOpenEngine, EntryMode, TradeDirection

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]
H = 3_600_000
FLAT = MarketContext(in_trade_window=True)


def t(h: int, day: int = 3) -> int:
    """Otvorenie 60m baru: 2. 9. 2025 (utorok) od 23:00, potom 3. 9. (streda)."""
    return int((datetime(2025, 9, day, 0, 0, tzinfo=NY) + timedelta(hours=h)).timestamp() * 1000)


def engine(**kw) -> DailyOpenEngine:
    return DailyOpenEngine(DailyOpenConfig(**kw), MNQ, 60)


def bar(ts: int, c: float, hi: float | None = None, lo: float | None = None) -> Bar:
    return Bar(ts, c, c + 2 if hi is None else hi, c - 2 if lo is None else lo, c, 100.0)


def night(e: DailyOpenEngine, closes) -> None:
    """Bar 23:00–0:00 (úroveň 20000) a nočné bary 0:00–7:00 s danými close."""
    e.on_bar(bar(t(-1), 20000.0), None, FLAT)
    for h, c in enumerate(closes):
        e.on_bar(bar(t(h), c), None, FLAT)


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


def test_uroven_je_zavretie_polnoci_a_od_8_stoji_stop_order():
    e = engine()
    night(e, [20005] * 7)                          # bary 0:00 … 6:00, posledný sa zavrie o 7:00
    assert e.d.level == 20000.0
    out = e.on_bar(bar(t(7), 20010), None, FLAT)   # zavretie 8:00
    oi = entries(out)[0]
    assert oi.order_type is OrderType.STOP and oi.direction is Direction.LONG
    assert (oi.plan.entry, oi.plan.stop_loss) == (20030, 19980)
    assert oi.plan.take_profit > 20030 + 1000       # bez cieľa — výstup v čase
    assert oi.plan.qty == 1.0


def test_pred_8_sa_nevstupuje_ani_pri_priearze():
    e = engine()
    e.on_bar(bar(t(-1), 20000.0), None, FLAT)
    for h in range(7):                              # zavretia 1:00 … 7:00 vysoko nad úrovňou
        assert not entries(e.on_bar(bar(t(h), 20100), None, FLAT))


def test_vstup_na_zavreti_nad_urovnou():
    e = engine(entryMode=EntryMode.CLOSE)
    night(e, [20005] * 7)
    assert not entries(e.on_bar(bar(t(7), 20025), None, FLAT))       # pod 20030
    oi = entries(e.on_bar(bar(t(8), 20040), None, FLAT))[0]          # zavretie 9:00 nad 20030
    assert oi.order_type is OrderType.MARKET and oi.plan.entry == 20040 and oi.plan.stop_loss == 19990


def test_prieraz_v_noci_ako_podmienka():
    e = engine(breakMode=BreakMode.BEFORE)
    e.on_bar(bar(t(-1), 20000.0), None, FLAT)
    for h in range(7):
        e.on_bar(bar(t(h), 19980, hi=19995), None, FLAT)              # celú noc pod úrovňou
    assert not entries(e.on_bar(bar(t(7), 19990, hi=19998), None, FLAT))
    e2 = engine(breakMode=BreakMode.BEFORE)
    night(e2, [20003] * 7)                                           # high 20005 nad úrovňou
    assert entries(e2.on_bar(bar(t(7), 20004), None, FLAT))


def test_nevyplneny_order_sa_zrusi_na_konci_okna_aj_s_boxmi():
    e = engine()
    night(e, [20005] * 7)
    oid = entries(e.on_bar(bar(t(7), 20010), None, FLAT))[0].order_id
    for h in range(8, 15):
        out = e.on_bar(bar(t(h), 20010), None, FLAT)
        assert not out.orders                                        # order stojí, nič nové
    out = e.on_bar(bar(t(15), 20010), None, FLAT)                    # zavretie 16:00
    assert [o.order_id for o in out.orders if o.action is OrderAction.CANCEL] == [oid]
    deleted = {getattr(d, "obj_id", "") for d in out.drawings if type(d).__name__ == "DrawDelete"}
    assert {f"do.tp.{t(7)}", f"do.sl.{t(7)}"} <= deleted


def test_vystup_o_16():
    e = engine()
    night(e, [20005] * 7)
    oid = entries(e.on_bar(bar(t(7), 20010), None, FLAT))[0].order_id
    pos = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({oid}))
    for h in range(8, 15):
        assert not e.on_bar(bar(t(h), 20040), None, pos).close_session
    out = e.on_bar(bar(t(15), 20040), None, pos)                     # zavretie 16:00
    assert out.close_session and [o.order_id for o in out.orders if o.action is OrderAction.CLOSE] == [oid]


def test_oba_smery_short_pod_urovnou_a_prehodenie_strany():
    e = engine(tradeDirection=TradeDirection.BOTH)
    night(e, [19990] * 7)
    oi = entries(e.on_bar(bar(t(7), 19985), None, FLAT))[0]          # cena pod úrovňou → short stop
    assert oi.direction is Direction.SHORT and oi.plan.entry == 19970 and oi.plan.stop_loss == 20020
    out = e.on_bar(bar(t(8), 20010), None, FLAT)                      # cena prešla nad úroveň
    assert [o.order_id for o in out.orders if o.action is OrderAction.CANCEL] == [oi.order_id]
    assert entries(out)[0].direction is Direction.LONG


def test_vyplnenie_a_stop_v_jednom_bare_nezmaze_boxy():
    """Adaptér hlási obchod otvorený aj zavretý vnútri baru cez `open_order_ids` pri nulovej pozícii."""
    e = engine()
    night(e, [20005] * 7)
    oid = entries(e.on_bar(bar(t(7), 20010), None, FLAT))[0].order_id
    round_trip = MarketContext(in_trade_window=True, position_size=0.0, open_order_ids=frozenset({oid}))
    e.on_bar(bar(t(8), 20000, hi=20035, lo=19975), None, round_trip)   # 20030 vyplnený a 19980 zasiahnutý
    assert e._pending is None
    for h in range(9, 16):
        out = e.on_bar(bar(t(h), 20010), None, FLAT)
        assert not any(type(d).__name__ == "DrawDelete" for d in out.drawings)
        assert not any(o.action is OrderAction.CANCEL for o in out.orders)


def test_bez_vystupu_v_case_drzi_do_stopu_alebo_ciela():
    """useExit vypnuté: žiadne zatvorenie v čase ani pri zmene dňa (len stop / cieľ)."""
    import pytest
    from tradebot.strategies.dailyopen import DailyOpenConfig
    with pytest.raises(Exception):
        DailyOpenConfig(useExit=False).validate()          # bez cieľa nemá obchod ako skončiť
    cfg = DailyOpenConfig(useExit=False, tpPts=40.0)
    cfg.validate()
    assert cfg.useExit is False and DailyOpenConfig().useExit is True


def test_bez_vystupu_v_case_nezatvara_o_16_ani_na_druhy_den():
    e = engine(useExit=False, tpPts=60.0)
    night(e, [20005] * 7)
    oid = entries(e.on_bar(bar(t(7), 20010), None, FLAT))[0].order_id
    pos = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({oid}))
    for h in range(8, 30):                                             # cez 16:00 aj polnoc do ďalšieho dňa
        assert not e.on_bar(bar(t(h), 20040), None, pos).close_session
