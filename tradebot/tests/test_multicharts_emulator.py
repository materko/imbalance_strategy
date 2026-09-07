"""Emulátor MultiCharts (webapp „burza" MultiCharts): broker, poplatky, súhrn, kresby, dáta."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from tradebot.adapters.multicharts.emulator import (
    EmulationResult, EmuTrade, bars_from_frame, emulate, rows_from_trades, summarize, write_chart,
)
from tradebot.adapters.multicharts.runner import BarOutput, LiveOrder
from tradebot.core import DrawRegistry, IBSConfig
from tradebot.core.risk import TradePlan
from tradebot.core.types import INSTRUMENTS, MNQ, Direction

MIN = 60_000
T0 = 1_736_121_600_000  # 2025-01-06 00:00 UTC


def m1_frame(rows):
    """rows = [(minutes_from_T0, o, h, l, c)] -> 1m DataFrame v tvare Freqtrade sviečok."""
    return pd.DataFrame({
        "date": [pd.Timestamp(T0 + m * MIN, unit="ms", tz="UTC") for m, *_ in rows],
        "open": [r[1] for r in rows], "high": [r[2] for r in rows], "low": [r[3] for r in rows],
        "close": [r[4] for r in rows], "volume": [1.0] * len(rows),
    })


def flat(minutes, price=100.0):
    return [(m, price, price, price, price) for m in minutes]


def plan(direction=Direction.LONG, entry=100.0, sl=99.0, tp=102.0, qty=2.0):
    return TradePlan(direction=direction, entry=entry, stop_loss=sl, take_profit=tp, qty=qty, sl_distance=abs(entry - sl))


def live(order_id, market=False, **kw):
    p = plan(**kw)
    return LiveOrder(order_id=order_id, source_id=1, direction=p.direction, plan=p, market=market)


def cfg():
    return IBSConfig(sess1On=True, sess1TZ="UTC", weekdaysOnly=False,
                     sess1ZoneStartH=0, sess1ZoneEndH=23, sess1TradeStartH=0, sess1TradeEndH=23)


def scripted(monkeypatch, outputs: dict[int, BarOutput]):
    """Runner vracia pripravený výstup podľa poradia baru (ostatné bary prázdne); zapisuje, čo dostal."""
    from tradebot.adapters.multicharts import runner as runner_mod

    seen = []

    def on_bar(self, bar, *, position_size=0.0, closed_trades=None):
        seen.append((bar.time, position_size, closed_trades))
        self.last_ts = bar.time
        return outputs.get(len(seen) - 1, BarOutput())

    monkeypatch.setattr(runner_mod.MCRunner, "on_bar", on_bar)
    return seen


# --------------------------------------------------------------------------- #


def test_bars_from_frame_sklada_3m_a_oreze_okno():
    df = m1_frame([(m, 100 + m, 101 + m, 99 + m, 100.5 + m) for m in range(9)])
    bars = bars_from_frame(df, 3, from_ms=T0 + 3 * MIN)
    assert [b.time for b in bars] == [T0 + 3 * MIN, T0 + 6 * MIN]
    assert (bars[0].open, bars[0].high, bars[0].low, bars[0].close, bars[0].volume) == (103, 106, 102, 105.5, 3)


def test_limitka_sa_vyplni_na_dalsom_bare_a_tp_po_1m(monkeypatch):
    # bar0 (0-3m): strategia zada limit 100; bar1: 1m sviecky: 101 (netrafi), 99.5 (trafi -> fill 100), 103 (TP 102)
    rows = flat([0, 1, 2], 101) + [(3, 101, 101.5, 100.8, 101), (4, 101, 101, 99.5, 100), (5, 100, 103, 100, 102.5)] + flat([6, 7, 8], 102)
    seen = scripted(monkeypatch, {0: BarOutput(entries=[live("LONG_1", entry=100.0, sl=99.0, tp=102.0, qty=2)])})
    result, _ = emulate(cfg(), MNQ, m1_frame(rows), 3)
    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.entry == 100.0 and t.exit == 102.0 and t.reason == "take_profit" and t.open_ms == T0 + 4 * MIN
    assert t.close_ms == T0 + 5 * MIN and result.ambiguous == 0
    # runner videl poziciu az na close baru 1... nie: obchod sa zavrel vnutri baru 1 -> na close je 0 a closed_trades=1
    assert seen[1] == (T0 + 3 * MIN, 0.0, 1)


def test_market_vstup_na_otvoreni_a_stop_loss_s_gapom(monkeypatch):
    rows = flat([0, 1, 2], 100) + [(3, 100, 100.5, 99.8, 100), (4, 98.0, 98.5, 97.5, 98), (5, 98, 98, 98, 98)] + flat([6, 7, 8], 98)
    scripted(monkeypatch, {0: BarOutput(entries=[live("PB_1", market=True, entry=100.0, sl=99.0, tp=103.0, qty=1)])})
    result, _ = emulate(cfg(), MNQ, m1_frame(rows), 3)
    t = result.trades[0]
    assert t.market and t.entry == 100.0 and t.open_ms == T0 + 3 * MIN
    assert t.exit == 98.0 and t.reason == "stop_loss"  # gap pod stop -> plni sa na open


def test_sl_a_tp_v_jednej_minute_berie_sl_a_pocita(monkeypatch):
    rows = flat([0, 1, 2], 100) + [(3, 100, 100, 100, 100), (4, 100, 103, 98, 100), (5, 100, 100, 100, 100)] + flat([6, 7, 8], 100)
    scripted(monkeypatch, {0: BarOutput(entries=[live("PB_1", market=True, entry=100.0, sl=99.0, tp=102.0, qty=1)])})
    result, _ = emulate(cfg(), MNQ, m1_frame(rows), 3)
    assert result.trades[0].reason == "stop_loss" and result.trades[0].exit == 99.0 and result.ambiguous == 1


def test_jedna_pozicia_a_trailing_stop_z_runnera(monkeypatch):
    # bar1: fill market 100; bar1 close: runner da exit_stop 101 (trailing); bar2: low 100.5 -> trailing_stop 101
    rows = (flat([0, 1, 2], 100) + [(3, 100, 102, 100, 101.8), (4, 101.8, 102.5, 101.5, 102), (5, 102, 102.2, 101.6, 102)]
            + [(6, 102, 102, 100.5, 100.6), (7, 100.6, 100.6, 100.6, 100.6), (8, 100.6, 100.6, 100.6, 100.6)])
    p = plan(entry=100.0, sl=99.0, tp=105.0, qty=1)
    scripted(monkeypatch, {
        0: BarOutput(entries=[live("PB_1", market=True, entry=100.0, sl=99.0, tp=105.0, qty=1), live("LONG_2", entry=100.0, qty=1)]),
        1: BarOutput(exit_plan=p, exit_stop=101.0),
    })
    result, _ = emulate(cfg(), MNQ, m1_frame(rows), 3)
    assert len(result.trades) == 1  # druhy vstup sa nevyplnil, kym bezala pozicia
    t = result.trades[0]
    assert t.exit == 101.0 and t.reason == "trailing_stop" and t.stop_last == 101.0 and t.max_price == 102.5


def test_koniec_seansy_zavrie_na_close_baru_a_koniec_dat_force_exit(monkeypatch):
    rows = flat([0, 1, 2], 100) + flat([3, 4, 5], 101) + flat([6, 7, 8], 103) + flat([9, 10, 11], 104)
    p = plan(entry=101.0, sl=90.0, tp=120.0, qty=1)
    scripted(monkeypatch, {
        0: BarOutput(entries=[live("PB_1", market=True, entry=101.0, sl=90.0, tp=120.0, qty=1)]),
        2: BarOutput(exit_plan=p, close_session=True),
        3: BarOutput(entries=[live("PB_2", market=True, entry=104.0, sl=90.0, tp=120.0, qty=1)]),
    })
    result, _ = emulate(cfg(), MNQ, m1_frame(rows), 3)
    assert [t.reason for t in result.trades] == ["session_end"]
    assert result.trades[0].exit == 103.0 and result.trades[0].close_ms == T0 + 6 * MIN
    # PB_2 zadany na poslednom bare sa uz nevyplni (dalsi bar nie je)


def test_riadky_poplatky_a_suhrn():
    t1 = EmuTrade("LONG_1", Direction.LONG, qty=2.0, entry=100.0, open_ms=T0, stop_initial=99.0, take_profit=102.0,
                  market=False, stop_last=99.0, exit=102.0, close_ms=T0 + 5 * MIN, reason="take_profit", max_price=102, min_price=99.5)
    t2 = EmuTrade("SHORT_2", Direction.SHORT, qty=1.0, entry=100.0, open_ms=T0 + 10 * MIN, stop_initial=101.0, take_profit=97.0,
                  market=True, stop_last=101.0, exit=101.0, close_ms=T0 + 12 * MIN, reason="stop_loss", max_price=101, min_price=99)
    inst = INSTRUMENTS["nas100_dukascopy"]  # point_value 1
    rows = rows_from_trades([t1, t2], inst, fee=0.001, leverage=10)
    r1, r2 = rows
    assert r1["profit_abs"] == pytest.approx(4.0 - 0.001 * (200 + 204), abs=1e-6)  # (102-100)*2 - poplatky
    assert r1["stake_amount"] == pytest.approx(200 / 10) and r1["is_short"] is False and r1["trade_duration"] == 5
    assert r2["profit_abs"] == pytest.approx(-1.0 - 0.001 * (100 + 101), abs=1e-6) and r2["is_short"] is True
    result = EmulationResult(trades=[t1, t2], bars=20, first_ms=T0, last_ms=T0 + 60 * MIN, first_close=100.0,
                             last_close=110.0, ambiguous=1, daily_closes=[(T0, 110.0)])
    summary, series = summarize(rows, 10000.0, result)
    assert summary["trades"] == 2 and summary["wins"] == 1 and summary["losses"] == 1 and summary["winrate"] == 50.0
    assert summary["gross_abs"] == 3.0 and summary["break_even_pct"] == pytest.approx(3.0 / (202 * 2 + 201) * 100, abs=1e-4)
    assert summary["max_drawdown_abs"] == pytest.approx(-r2["profit_abs"], abs=0.01)
    assert summary["market_change_pct"] == 10.0 and summary["exits"]["take_profit"]["n"] == 1
    assert summary["engine"] == "multicharts-emulator" and summary["ambiguous_minutes"] == 1
    assert len(series["equity"]) == 2 and series["market"] == [[series["market"][0][0], 10.0]]


def test_write_chart_ma_tvar_freqtrade_exportu(tmp_path: Path, monkeypatch):
    rows = flat(range(0, 12), 100)
    scripted(monkeypatch, {})
    registry = DrawRegistry()
    result, runner = emulate(cfg(), MNQ, m1_frame(rows), 3, registry=registry)
    header = write_chart(runner, registry, result, "NAS100/USD", "3m", tmp_path / "chart.json.gz")
    assert header["pair"] == "NAS100/USD" and header["bars"] == 4 and header["from_ms"] == T0
    import gzip
    import json

    data = json.load(gzip.open(tmp_path / "chart.json.gz", "rt", encoding="utf-8"))
    assert set(data) >= {"version", "strategy", "pair", "timeframe", "from_ms", "to_ms", "bars", "counts", "objects"}


def test_cely_engine_bezi_nad_1m_datami_bez_skriptovania():
    """Skutočný engine IBS nad syntetickými dátami — nič nespadne, bary sa spočítajú."""
    import random

    random.seed(1)
    price = 20000.0
    rows = []
    for m in range(0, 60 * 24):
        o = price
        h = o + random.uniform(0, 8)
        l = o - random.uniform(0, 8)
        c = random.uniform(l, h)
        rows.append((m, o, h, l, c))
        price = c
    cfg_, inst = IBSConfig(), INSTRUMENTS["nas100_dukascopy"]
    result, _ = emulate(cfg_, inst, m1_frame(rows), 3)
    assert result.bars == 480 and result.first_ms == T0
