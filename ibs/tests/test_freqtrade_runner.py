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
    """bars[0] = Pine `[1]` nad sériou, ktorú vidí `request.security(lookahead_off)`.

    Na 3m grafe s 5m detekciou sa Pine rozhoduje pri UZAVRETÍ baru grafu. Na bare
    T0 (uzavrie sa T0+3m) je posledný uzavretý 5m bar ten s otvorením T0−5m, a
    offset `[1]` vo výraze security posunie okno ešte o jeden bar dozadu.
    Počítať okno z otváracieho času baru dávalo v TradingView 104 zón namiesto 77.
    """
    bars = _htf_bars(10)
    sma = dict.fromkeys(bars, 100.0)
    runner.htf_window_for(T0, bars, sma)
    runner.htf_window_for(T0 + MIN3, bars, sma)  # stále tá istá 5m perióda
    win = runner.htf_window_for(T0 + 2 * MIN3, bars, sma)

    assert win.bars[0].time == T0 - MIN5
    assert [b.time for b in win.bars] == [T0 - (1 + i) * MIN5 for i in range(4)]


def test_htf_window_offset_nie_je_konstantny(runner):
    """Mriežky 3m a 5m sa neprekrývajú, takže posun okna sa v 15-minútovom cykle mení."""
    bars = _htf_bars(20)
    sma = dict.fromkeys(bars, 100.0)

    seen = {}
    for i in range(11):  # T0 .. T0+30m
        win = runner.htf_window_for(T0 + i * MIN3, bars, sma)
        if win is not None:
            seen[i * 3] = (win.bars[0].time - T0) // MIN5

    # novú 5m periódu začínajú bary grafu na 6, 12, 15, 21, 27 a 30 minúte
    assert seen == {6: -1, 12: 1, 15: 1, 21: 2, 27: 4, 30: 4}


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
