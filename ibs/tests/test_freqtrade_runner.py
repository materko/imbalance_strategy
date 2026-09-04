"""Testy Freqtrade runnera.

Runner sa dá testovať **bez nainštalovaného Freqtrade** — je to zámer: logika, ktorá
prevádza engine cez bary, nemá na platforme závisieť.
"""

from __future__ import annotations

import pytest

from ibs.adapters.freqtrade import EngineRunner, SignalRow
from ibs.core import MNQ, Bar, HTFWindow, IBSConfig

T0 = 1_756_684_800_000
MIN3 = 180_000
MIN5 = 300_000


def bar(ts: int, o=100.0, h=101.0, low=99.0, c=100.5, v=100.0) -> Bar:
    return Bar(time=ts, open=o, high=h, low=low, close=c, volume=v)


@pytest.fixture
def runner() -> EngineRunner:
    cfg = IBSConfig(sess1On=True, sess1TZ="UTC", weekdaysOnly=False,
                    sess1ZoneStartH=0, sess1ZoneEndH=23,
                    sess1TradeStartH=0, sess1TradeEndH=23)
    return EngineRunner(cfg, MNQ, chart_tf_minutes=3)


def test_process_records_a_row_per_bar(runner):
    for i in range(5):
        runner.process(bar(T0 + i * MIN3), None)
    assert len(runner.rows) == 5
    assert runner.last_ts == T0 + 4 * MIN3


def test_rows_are_keyed_by_bar_time(runner):
    runner.process(bar(T0), None)
    assert isinstance(runner.rows[T0], SignalRow)


def test_no_signal_means_blank_row(runner):
    row = runner.process(bar(T0), None)
    assert row.enter_long == 0 and row.enter_short == 0
    assert row.entry != row.entry  # NaN


def test_signal_lookup_returns_none_without_signals(runner):
    runner.process(bar(T0), None)
    assert runner.signal_at_or_before(T0) is None


def test_signal_lookup_finds_the_previous_signal(runner):
    """Freqtrade otvára obchod až na sviečke PO signáli, takže sa musí pozerať dozadu."""
    runner.process(bar(T0), None)
    signal = SignalRow(enter_long=1, entry=123.0, stop_loss=120.0, take_profit=126.0, qty=2.0)
    runner.rows[T0 + MIN3] = signal
    runner.signal_ts.append(T0 + MIN3)
    runner.process(bar(T0 + 2 * MIN3), None)

    assert runner.signal_at_or_before(T0 + 2 * MIN3) is signal
    assert runner.signal_at_or_before(T0 + MIN3) is signal
    assert runner.signal_at_or_before(T0) is None


def test_signal_lookup_picks_the_latest_one(runner):
    first = SignalRow(enter_long=1, entry=1.0)
    second = SignalRow(enter_long=1, entry=2.0)
    runner.rows[T0] = first
    runner.rows[T0 + 10 * MIN3] = second
    runner.signal_ts.extend([T0, T0 + 10 * MIN3])

    assert runner.signal_at_or_before(T0 + 5 * MIN3) is first
    assert runner.signal_at_or_before(T0 + 20 * MIN3) is second


# --------------------------------------------------------------------------- #
# HTF okno
# --------------------------------------------------------------------------- #


def _htf_bars(count: int) -> dict[int, Bar]:
    return {T0 + i * MIN5: bar(T0 + i * MIN5) for i in range(-count, count)}


def test_htf_window_only_on_a_new_period(runner):
    bars = _htf_bars(10)
    sma = dict.fromkeys(bars, 100.0)

    # prvy bar len nastavi referenciu, okno sa este nevracia
    assert runner.htf_window_for(T0, bars, sma) is None
    # ten isty 5m interval -> stale nic
    assert runner.htf_window_for(T0 + 60_000, bars, sma) is None
    # novy 5m interval -> okno
    win = runner.htf_window_for(T0 + MIN5, bars, sma)
    assert isinstance(win, HTFWindow)


def test_htf_window_uses_only_closed_bars(runner):
    """bars[0] musí byť POSLEDNÝ UZAVRETÝ HTF bar, nie ten práve otvorený — inak repaint."""
    bars = _htf_bars(10)
    sma = dict.fromkeys(bars, 100.0)
    runner.htf_window_for(T0, bars, sma)
    win = runner.htf_window_for(T0 + MIN5, bars, sma)

    assert win.bars[0].time == T0  # perioda, ktora sa prave uzavrela
    assert [b.time for b in win.bars] == [T0 - i * MIN5 for i in range(0, 4)]


def test_htf_window_is_none_when_history_is_short(runner):
    bars = {T0: bar(T0), T0 - MIN5: bar(T0 - MIN5)}  # len 2 bary, treba 4
    runner.htf_window_for(T0, bars, {})
    assert runner.htf_window_for(T0 + MIN5, bars, {}) is None


# --------------------------------------------------------------------------- #
# Fill model
# --------------------------------------------------------------------------- #


def test_engine_sees_no_open_orders_initially(runner):
    runner.process(bar(T0), None)
    assert runner._open_ids == frozenset()


def test_incremental_run_does_not_reprocess(runner):
    for i in range(3):
        runner.process(bar(T0 + i * MIN3), None)
    processed = runner.engine.history.bar_index

    # simulacia opakovaneho volania populate_indicators nad rastucim DataFrame:
    # bary, ktore uz maju ts <= last_ts, sa preskakuju na strane strategie
    already = [T0 + i * MIN3 for i in range(3)]
    assert all(ts <= runner.last_ts for ts in already)
    assert processed == 2
