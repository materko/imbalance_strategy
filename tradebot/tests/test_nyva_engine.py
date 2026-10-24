"""NY VA BREAKOUT 1.0: profil prvej hodiny a prieraz z value area na syntetických 3m baroch MNQ (mechanika)."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction
from tradebot.strategies.nyva import NyVaConfig, NyVaEngine
from tradebot.strategies.nyva.engine import value_area

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]


def ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def test_value_area_poc_v_najobjemnejsom_riadku():
    bars = [(101.0, 100.0, 10.0), (105.0, 104.0, 100.0), (110.0, 109.0, 10.0)]
    poc, vah, val, hi, lo = value_area(bars, 10, 70.0, 0.25)
    assert (hi, lo) == (110.0, 100.0)
    assert 104.0 <= poc <= 105.0
    assert val <= poc <= vah and vah <= hi and val >= lo


def run(cfg: NyVaConfig, closes: dict[str, float], base: float = 100.0):
    """3m bary 9:00–12:00 NY; v range objem okolo `base`, po rangei zavretia podľa `closes` (HH:MM → cena)."""
    e = NyVaEngine(cfg, MNQ, 3)
    t, pos, log = datetime(2025, 10, 7, 9, 0, tzinfo=NY), 0.0, []
    while t < datetime(2025, 10, 7, 12, 0, tzinfo=NY):
        c = closes.get(t.strftime("%H:%M"), base)
        out = e.on_bar(Bar(ms(t), c, c + 1, c - 1, c, 100.0), None,
                       MarketContext(in_trade_window=True, position_size=pos, open_order_ids=("nv",) if pos else ()))
        for o in out.orders:
            if o.action is OrderAction.ENTRY:
                log.append((t.strftime("%H:%M"), o.plan))
                pos = 1.0
        t += timedelta(minutes=3)
    return e, log


def test_long_nad_vah_stop_za_poc_ciel_rr():
    cfg = NyVaConfig(rrRatio=2.0, slBufferTicks=4)
    e, log = run(cfg, {"10:45": 110.0})
    assert [t for t, _ in log] == ["10:45"]
    plan = log[0][1]
    assert plan.direction is Direction.LONG
    assert plan.stop_loss == MNQ.round_price(e.poc - 4 * MNQ.tick_size)
    assert abs(plan.take_profit - (110.0 + 2.0 * (110.0 - plan.stop_loss))) <= MNQ.tick_size


def test_short_pod_val_a_bez_vstupu_v_range_a_po_konci():
    _, log = run(NyVaConfig(), {"10:00": 80.0, "10:51": 90.0})
    assert [(t, p.direction) for t, p in log] == [("10:51", Direction.SHORT)]
    _, log = run(NyVaConfig(entryEndH=10, entryEndM=45), {"10:51": 90.0})
    assert log == []
    _, log = run(NyVaConfig(allowShort=False), {"10:51": 90.0})
    assert log == []


def test_potvrdenie_dvoma_zavretiami():
    _, log = run(NyVaConfig(confirmCloses=2), {"10:45": 110.0, "10:48": 110.0})
    assert [t for t, _ in log] == ["10:48"]
    _, log = run(NyVaConfig(confirmCloses=2), {"10:45": 110.0})
    assert log == []


def test_max_stop_vynecha_alebo_skrati():
    _, log = run(NyVaConfig(maxSlPoints=2.0), {"10:45": 110.0})
    assert log == []
    _, log = run(NyVaConfig(maxSlPoints=2.0, slCapMode="cap"), {"10:45": 110.0})
    assert abs(log[0][1].stop_loss - 108.0) <= MNQ.tick_size


def test_sirka_va_a_vwap_filter():
    _, log = run(NyVaConfig(vaMaxPoints=0.5), {"10:45": 110.0})
    assert log == []
    _, log = run(NyVaConfig(useVwap=True), {"10:45": 110.0})
    assert [t for t, _ in log] == ["10:45"]          # 110 je nad VWAP dňa (~100)


def test_retest_limitka_na_vah():
    from tradebot.core.types import OrderType
    e = NyVaEngine(NyVaConfig(entryMode="retest", retestBars=2), MNQ, 3)
    t, kinds = datetime(2025, 10, 7, 9, 0, tzinfo=NY), []
    while t < datetime(2025, 10, 7, 11, 0, tzinfo=NY):
        c = 110.0 if t.strftime("%H:%M") == "10:45" else 100.0 if t.hour < 10 or t.minute < 30 else 111.0 if t.minute > 45 else 100.0
        out = e.on_bar(Bar(ms(t), c, c + 1, c - 1, c, 100.0), None, MarketContext(in_trade_window=True))
        kinds += [(t.strftime("%H:%M"), o.action, o.order_type, o.plan.entry if o.plan else None) for o in out.orders]
        t += timedelta(minutes=3)
    assert kinds[0][:3] == ("10:45", OrderAction.ENTRY, OrderType.LIMIT)
    assert abs(kinds[0][3] - e.vah) <= MNQ.tick_size
    assert kinds[1][:2] == ("10:51", OrderAction.CANCEL)


def test_tvar_profilu_p_a_b():
    from tradebot.strategies.nyva.engine import profile_shape
    p = profile_shape([(110.0, 107.0, 100.0), (110.0, 106.0, 100.0), (108.0, 100.0, 10.0)], 30, 70.0, 0.25)
    assert p["poc"] > 0.6 and p["va"] > 0.55 and p["low"] < 0.25
    b = profile_shape([(103.0, 100.0, 100.0), (104.0, 100.0, 100.0), (110.0, 102.0, 10.0)], 30, 70.0, 0.25)
    assert b["poc"] < 0.4 and b["va"] < 0.45 and b["high"] < 0.25


def test_nyvashape_ma_tvar_zapnuty():
    from tradebot.strategies import STRATEGIES
    assert STRATEGIES["nyvashape"].config_cls().useShape is True
    assert STRATEGIES["nyva"].config_cls().useShape is False
