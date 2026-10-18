"""NOC + PONDELOK 1.0: engine na syntetických 5m baroch MNQ (mechanika, nie edge)."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, OrderType
from tradebot.strategies.nocpon import NocPonConfig, NocPonEngine

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]
STEP = 300_000


def ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def run(cfg: NocPonConfig, start: datetime, end: datetime, price=lambda i: 100.0, pos_after_entry=True):
    """Bary 5m 24/5 (bez 17:00–18:00 a víkendu), pozícia sa „vyplní“ na ďalšom bare po ENTRY a zavrie po close_session."""
    e = NocPonEngine(cfg, MNQ, 5)
    t, i, pos, log = start, 0, 0.0, []
    while t < end:
        loc = t.astimezone(NY)
        closed_mkt = loc.hour == 17 or loc.weekday() == 5 or (loc.weekday() == 4 and loc.hour >= 17) or (loc.weekday() == 6 and loc.hour < 18)
        if not closed_mkt:
            p = price(i)
            out = e.on_bar(Bar(ms(t), p, p + 1, p - 1, p, 10.0), None,
                           MarketContext(in_trade_window=True, position_size=pos, open_order_ids=("np",) if pos else ()))
            for o in out.orders:
                if o.action is OrderAction.ENTRY:
                    log.append(("ENTRY", (t + timedelta(minutes=5)).astimezone(NY), o.order_type))
                    pos = 1.0 if pos_after_entry else pos
            if out.close_session and pos:
                log.append(("CLOSE", (t + timedelta(minutes=5)).astimezone(NY), None))
                pos = 0.0
            i += 1
        t += timedelta(minutes=5)
    return e, log


def test_noc_vstup_1555_vystup_3_00():
    cfg = NocPonConfig(useTrend=False, useMonday=False, skipRoll=False)
    _, log = run(cfg, datetime(2025, 10, 7, 9, 0, tzinfo=NY), datetime(2025, 10, 8, 10, 0, tzinfo=NY))   # ut → st
    assert [(a, t.strftime("%a %H:%M")) for a, t, _ in log] == [("ENTRY", "Tue 15:55"), ("CLOSE", "Wed 03:00")]
    assert log[0][2] is OrderType.MARKET


def test_piatok_drzi_do_pondelka_a_pondelok_prechadza_do_noci():
    cfg = NocPonConfig(useTrend=False, skipRoll=False)
    _, log = run(cfg, datetime(2025, 10, 10, 9, 0, tzinfo=NY), datetime(2025, 10, 14, 4, 0, tzinfo=NY))   # pi → ut
    got = [(a, t.strftime("%a %H:%M")) for a, t, _ in log]
    assert got[:2] == [("ENTRY", "Fri 15:55"), ("CLOSE", "Mon 03:00")]
    # pondelok 9:30 vstup, o 15:55 sa len predĺži do noci → výstup utorok 3:00
    assert got[2:] == [("ENTRY", "Mon 09:30"), ("CLOSE", "Tue 03:00")]


def test_trend_a_roll():
    # bez histórie SMA nie je trend → nič
    _, log = run(NocPonConfig(skipRoll=False, smaLen=3), datetime(2025, 10, 6, 9, 0, tzinfo=NY), datetime(2025, 10, 7, 20, 0, tzinfo=NY))
    assert log == []
    # rastúca cena: po 3 denných zavretiach je cena nad SMA → noc sa obchoduje
    _, log = run(NocPonConfig(skipRoll=False, smaLen=3, useMonday=False), datetime(2025, 10, 6, 9, 0, tzinfo=NY),
                 datetime(2025, 10, 10, 10, 0, tzinfo=NY), price=lambda i: 100.0 + i * 0.1)
    assert [t.strftime("%a %H:%M") for a, t, _ in log if a == "ENTRY"] == ["Wed 15:55", "Thu 15:55"]
    # roll okno (december 7.–16.) noc vynechá
    _, log = run(NocPonConfig(useTrend=False, useMonday=False), datetime(2025, 12, 9, 9, 0, tzinfo=NY),
                 datetime(2025, 12, 10, 10, 0, tzinfo=NY))
    assert log == []
