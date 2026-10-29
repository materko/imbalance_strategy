"""SPRÁVY 1.0: kalendár (časové pásma, posun času, opravy z profilu) a engine na syntetických 5m baroch."""

from __future__ import annotations

from datetime import date, datetime, timezone

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.spravy import SpravyConfig, SpravyEngine
from tradebot.strategies.spravy.calendar import events_utc, load, to_utc_ms
from tradebot.strategies.spravy.engine import sk_time

MGC = INSTRUMENTS["mgc_databento"]
M5 = 5 * 60_000
FLAT = MarketContext(in_trade_window=True)


def utc(y, m, d, hh, mm) -> int:
    return int(datetime(y, m, d, hh, mm, tzinfo=timezone.utc).timestamp() * 1000)


# ---------------------------------------------------------------- kalendár / čas
def test_fomc_28_10_2026_je_o_19_u_nas():
    """Slovensko prešlo na zimný čas 25. 10., USA až 1. 11. — FOMC 14:00 NY je 19:00 SK, nie 20:00."""
    t = to_utc_ms(date(2026, 10, 28), "14:00")
    assert t == utc(2026, 10, 28, 18, 0)
    assert sk_time(t).startswith("19:00 SK")
    assert sk_time(to_utc_ms(date(2026, 11, 4), "14:00")).startswith("20:00 SK")     # po 1. 11. zase +6 h


def test_marec_usa_skor_v_lete():
    """USA na letný čas 8. 3. 2026, Slovensko 29. 3. — CPI 8:30 NY je vtedy 13:30 SK."""
    assert sk_time(to_utc_ms(date(2026, 3, 11), "08:30")).startswith("13:30 SK")
    assert sk_time(to_utc_ms(date(2026, 4, 10), "08:30")).startswith("14:30 SK")
    assert sk_time(to_utc_ms(date(2026, 1, 13), "08:30")).startswith("14:30 SK")


def test_kalendar_ma_vsetky_typy_a_presny_fomc():
    ev = load()["events"]
    assert {"FOMC", "CPI", "NFP", "PPI", "PCE", "GDP", "JOLTS", "RETAIL", "ISM_M", "ISM_S", "FOMC_MIN", "CLAIMS"} <= set(ev)
    assert "2026-10-28" in ev["FOMC"]["dates"] and ev["FOMC"]["time_et"] == "14:00"


def test_opravy_z_profilu():
    base = events_utc({"PPI"})
    moved = events_utc({"PPI"}, add="2026-11-26 08:30 PPI", skip="2026-11-13 PPI")
    assert (to_utc_ms(date(2026, 11, 13), "08:30"), "PPI") in base
    assert (to_utc_ms(date(2026, 11, 13), "08:30"), "PPI") not in moved
    assert (to_utc_ms(date(2026, 11, 26), "08:30"), "PPI") in moved


# ---------------------------------------------------------------- engine
def run(cfg: SpravyConfig, bars):
    e = SpravyEngine(cfg, MGC, 5)
    outs = [e.on_bar(Bar(t, o, h, l, c, 100.0), None, FLAT) for t, o, h, l, c in bars]
    return e, outs


def path(t0: int, n: int, start: float, step: float):
    """n 5m barov od t0, cena ide o `step` za bar."""
    out, p = [], start
    for i in range(n):
        o, c = p, p + step
        out.append((t0 + i * M5, o, max(o, c) + 0.2, min(o, c) - 0.2, c))
        p = c
    return out


def entries(outs):
    return [o for out in outs for o in out.orders if o.action is OrderAction.ENTRY]


def test_fomc_trend_long_po_rastucej_nohe_15_60():
    t = to_utc_ms(date(2026, 10, 28), "14:00")
    cfg = SpravyConfig(trendEvents="FOMC", fadeEvents="", atrLen=3)
    bars = path(t - 6 * M5, 6, 4000, 0.1) + path(t, 24, 4000.6, 1.0)      # od správy rast o 1 bod / 5 min
    e, outs = run(cfg, bars)
    en = entries(outs)
    assert len(en) == 1
    o = en[0]
    assert o.order_type is OrderType.MARKET and o.direction is Direction.LONG
    i = next(k for k, out in enumerate(outs) if out.orders)
    assert bars[i][0] + M5 == t + 60 * 60_000                             # vstup na konci nohy T+60
    assert o.plan.stop_loss < o.plan.entry
    assert "19:00 SK" in o.reason


def test_cpi_fade_short_po_rastucej_nohe():
    t = to_utc_ms(date(2026, 9, 11), "08:30")
    t = next(x for x, typ in events_utc({"CPI"}) if x >= t)
    cfg = SpravyConfig(trendEvents="", fadeEvents="CPI", atrLen=3)
    bars = path(t - 6 * M5, 6, 4000, 0.1) + path(t, 16, 4000.6, 1.0)
    _, outs = run(cfg, bars)
    o = entries(outs)[0]
    assert o.direction is Direction.SHORT and o.plan.stop_loss > o.plan.entry


def test_vystup_v_case_po_drzani():
    t = to_utc_ms(date(2026, 10, 28), "14:00")
    cfg = SpravyConfig(trendEvents="FOMC", fadeEvents="", atrLen=3, trendHold=30)
    e = SpravyEngine(cfg, MGC, 5)
    bars = path(t - 6 * M5, 6, 4000, 0.1) + path(t, 30, 4000.6, 1.0)
    closes = []
    for k, (tt, o, h, l, c) in enumerate(bars):
        entered = any(x.action is OrderAction.ENTRY for x in e.on_bar(Bar(tt, o, h, l, c, 1.0), None, FLAT).orders) if k < 18 else False
        if entered:
            entry_end = tt + M5
            break
    pos = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({"x"}))
    for tt, o, h, l, c in bars[k + 1:]:
        out = e.on_bar(Bar(tt, o, h, l, c, 1.0), None, pos)
        if any(x.action is OrderAction.CLOSE for x in out.orders):
            closes.append(tt + M5)
            break
    assert closes and closes[0] >= entry_end + 30 * 60_000


def test_nezname_typy_su_chyba():
    import pytest

    from tradebot.core.config import ConfigError

    with pytest.raises(ConfigError, match="XYZ"):
        SpravyConfig(trendEvents="FOMC,XYZ")
    with pytest.raises(ConfigError, match="naraz"):
        SpravyConfig(trendEvents="CPI", fadeEvents="CPI")
