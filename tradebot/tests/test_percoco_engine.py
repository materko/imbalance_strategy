"""Craig Percoco 1.0: engine na syntetických 1m sviečkach.

Testuje sa mechanika z videa: CHoCH na grafe (zavretie nad posledný swing high po poklese), FVG
v pohybe CHoCH, limitka na jeho stred, stop pod low pohybu, cieľ 4R; filtre 15m (smer, dotyk FVG);
kresba obchodu až pri vyplnení a zánik setupu.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.percoco import PercocoConfig, PercocoEngine

NY = ZoneInfo("America/New_York")
T0 = int(datetime(2025, 9, 2, 10, 0, tzinfo=NY).timestamp() * 1000)
M1 = 60_000
FLAT = MarketContext(in_trade_window=True)
BTC = INSTRUMENTS["btcusdt_binance"]

#: pokles s nižším low (BOS dole), potom rally s FVG a zavretie nad posledný swing high 110 (CHoCH hore)
ROWS = [(105, 106, 104, 105), (105, 105.5, 103, 104), (104, 108, 103.5, 107.5), (107.5, 110, 107, 109),
        (109, 109.5, 104, 104.5), (104.5, 105, 101, 101.5), (101.5, 102, 100, 100.5), (100.5, 101, 99, 100.8),
        (100.8, 104, 100.5, 103.8), (103.8, 108, 104.5, 107.6), (107.6, 111, 107, 110.5)]


def _cfg(**kw) -> PercocoConfig:
    base = dict(htfTF=5, swingLen=1, atrLen=3, useHtfBias=False, useHtfPoi=False, useTradeWindow=False,
                weekdaysOnly=False, rrRatio=4.0, showHtfFvg=False)
    base.update(kw)
    return PercocoConfig(**base)


def _bar(i, o, h, lo, c):
    return Bar(time=T0 + i * M1, open=o, high=h, low=lo, close=c, volume=10.0)


def _run(e, rows, start=0, ctx=FLAT):
    return [e.on_bar(_bar(start + i, *r), None, ctx) for i, r in enumerate(rows)]


def _entries(outs):
    return [o for out in outs for o in out.orders if o.action is OrderAction.ENTRY]


def test_choch_fvg_limitka_na_stred_stop_pod_low_pohybu_ciel_4r():
    e = PercocoEngine(_cfg(), BTC, 1)
    outs = _run(e, ROWS)
    assert not _entries(outs[:10]), "pred CHoCH sa nevstupuje"
    o = _entries(outs[10:])[0]
    assert o.direction is Direction.LONG and o.order_type is OrderType.LIMIT
    # posledné FVG v pohybe: high sviečky 8 (104) – low sviečky 10 (107) → stred 105,5; low pohybu 99
    assert (o.plan.entry, o.plan.stop_loss, o.plan.take_profit) == (105.5, 99.0, 131.5)


def test_kresba_obchodu_az_pri_vyplneni():
    e = PercocoEngine(_cfg(), BTC, 1)
    outs = _run(e, ROWS)
    kinds = lambda out: {str(d.kind.value) for d in out.drawings if hasattr(d, "kind")}
    assert not any("pc_entry" in kinds(o) or "tp_box" in kinds(o) for o in outs), "limitka ešte nie je obchod"
    fill = _run(e, [(110.5, 111, 105, 106)], start=len(ROWS))[0]           # cena príde na 105,5
    assert {"pc_entry", "tp_box", "sl_box", "pc_fvg"} <= kinds(fill)
    assert e.setup is None and e._trades_today == 1


def test_nevyplnena_limitka_sa_posiela_znova_a_setup_zanikne_pri_cieli():
    e = PercocoEngine(_cfg(setupMaxBars=50), BTC, 1)
    _run(e, ROWS)
    away = _run(e, [(110.5, 112, 108, 111), (111, 113, 109, 112)], start=len(ROWS))
    assert [o.action for o in away[0].orders] == [OrderAction.CANCEL, OrderAction.ENTRY], "limitka platí jednu sviečku"
    gone = _run(e, [(112, 132, 111, 131)], start=len(ROWS) + 2)[0]           # cieľ 131,5 dosiahnutý bez vyplnenia
    assert e.setup is None and not _entries([gone])
    assert not any(str(getattr(d.kind, "value", "")) == "pc_entry" for d in gone.drawings)


def test_setup_padne_ked_cena_zavrie_pod_stop():
    e = PercocoEngine(_cfg(), BTC, 1)
    _run(e, ROWS)
    _run(e, [(110.5, 111, 106, 107)], start=len(ROWS))       # nevyplní (low 106 > 105,5)
    _run(e, [(107, 107.5, 98, 98.5)], start=len(ROWS) + 1)   # prejde limitkou a zavrie pod stop
    assert e.setup is None


def test_filter_15m_dotyk_fvg_bez_dotyku_nic():
    e = PercocoEngine(_cfg(useHtfPoi=True), BTC, 1)
    assert not _entries(_run(e, ROWS)), "bez dotyku 15m FVG sa CHoCH neobchoduje"


def test_filter_15m_smer():
    e = PercocoEngine(_cfg(useHtfBias=True), BTC, 1)
    assert e.h_trend == 0
    assert not _entries(_run(e, ROWS)), "bez 15m trendu hore sa long neobchoduje"


def test_short_only_long_nepusti():
    e = PercocoEngine(_cfg(tradeDirection="Short only"), BTC, 1)
    assert not _entries(_run(e, ROWS))
