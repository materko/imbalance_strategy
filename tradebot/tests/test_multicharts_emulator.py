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

    def on_bar(self, bar, *, position_size=0.0, closed_trades=None, closed_trade_pnls=None):
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


# --------------------------------------------------------------------------- #
# HTF okno: emulátor kŕmi feeder pred `on_bar`, ako študia (audit A2)
# --------------------------------------------------------------------------- #


class _SpyEngine:
    """Engine, ktorý nič neobchoduje, len si zapíše okná a kontext."""

    def __init__(self, *args):
        self.windows: list[tuple[int, int, float]] = []
        self.contexts = []

    def on_bar(self, bar, htf=None, ctx=None):
        from tradebot.core.engine import EngineOutput

        self.contexts.append((bar.time, ctx))
        if htf is not None:
            self.windows.append((bar.time, tuple(b.time for b in htf.bars), htf.vol_sma))
        return EngineOutput()


def _spy_spec(engine=_SpyEngine):
    from dataclasses import replace

    from tradebot.strategies import get_spec

    return replace(get_spec("ibs"), engine_factory=engine)


def _varied(minutes: int, start: int = 0):
    """1m rady s meniacim sa objemom — nech sa porovná aj SMA objemu okna."""
    df = m1_frame([(m, 100.0 + m % 7, 101.0 + m % 7, 99.0 + m % 7, 100.0 + m % 5) for m in range(start, start + minutes)])
    df["volume"] = [1.0 + (m * 37) % 11 for m in range(len(df))]
    return df


@pytest.mark.parametrize("chart_tf,detection_tf", [(3, "5"), (5, "5"), (5, "3"), (10, "5"), (15, "5")])
def test_htf_okna_emulatora_sedia_s_feederom_s_celymi_datami(chart_tf, detection_tf):
    from tradebot.strategies.ibs.htf import HTFFeeder

    cfg_ = IBSConfig(zoneDetectionTF=detection_tf, volSmaLen=3)
    data = _varied(240)
    _, runner = emulate(cfg_, MNQ, data, chart_tf, spec=_spy_spec())

    full = HTFFeeder(cfg_, chart_tf)
    for b in bars_from_frame(data, int(detection_tf)):
        full.feed(b)
    reference = []
    for b in bars_from_frame(data, chart_tf):
        w = full.window_for(b.time)
        if w is not None:
            reference.append((b.time, tuple(x.time for x in w.bars), w.vol_sma))

    assert len(reference) > 0
    assert runner.engine.windows == reference


def test_htf_okno_3m_graf_5m_detekcia_drzi_golden_casovanie():
    """Na 3m/5m je najnovší bar okna (Pine [1]) dva 5m bary pred zatvorením 3m baru."""
    cfg_ = IBSConfig(zoneDetectionTF="5", volSmaLen=3)
    _, runner = emulate(cfg_, MNQ, _varied(120), 3, spec=_spy_spec())
    for ts, opens, _sma in runner.engine.windows:
        close = ts + 3 * MIN
        assert opens[0] == close // (5 * MIN) * (5 * MIN) - 10 * MIN
        assert opens[0] + 5 * MIN <= close - 5 * MIN  # uzavretý o celý HTF bar skôr — žiadny lookahead


def test_denny_detekcny_tf_d_nespadne_a_da_okna():
    from tradebot.strategies import get_spec

    cfg_ = IBSConfig(zoneDetectionTF="D", volSmaLen=2)
    assert get_spec("ibs").informative_tfs(cfg_) == ["1d"]
    data = m1_frame(flat(range(0, 6 * 1440, 10)))  # 6 dní, sviečka každých 10 minút
    _, runner = emulate(cfg_, MNQ, data, 60, spec=_spy_spec())
    assert runner.htf_ms == 86_400_000
    days = [opens for _ts, opens, _sma in runner.engine.windows]
    assert days and all(o % 86_400_000 == 0 for opens in days for o in opens)


# --------------------------------------------------------------------------- #
# maxDailyWins cez emulátor (audit A5)
# --------------------------------------------------------------------------- #


class _EveryBarLong:
    """Market long na každom bare bez pozície, kým kontext nepovie „denný limit"."""

    tp = 0.5
    sl = 100.0

    def __init__(self, *args):
        self.limits: list[tuple[int, bool]] = []

    def on_bar(self, bar, htf=None, ctx=None):
        from tradebot.core.engine import EngineOutput
        from tradebot.core.orders import OrderAction, OrderIntent
        from tradebot.core.types import OrderType

        self.limits.append((bar.time, ctx.daily_win_limit_reached))
        if ctx.position_size != 0.0 or ctx.daily_win_limit_reached:
            return EngineOutput(orders=[OrderIntent(OrderAction.CANCEL, "L", 1)])
        p = TradePlan(direction=Direction.LONG, entry=bar.close, stop_loss=bar.close - self.sl,
                      take_profit=bar.close + self.tp, qty=1.0, sl_distance=self.sl)
        return EngineOutput(orders=[OrderIntent(OrderAction.ENTRY, "L", 1, Direction.LONG, p, OrderType.MARKET)])


def _day(ms: int) -> int:
    return ms // 86_400_000


def test_max_daily_wins_zastavi_vstupy_do_konca_dna_a_na_druhy_den_pusti():
    # rastúca cena od 22:00 do 02:00 -> každý market long trafí TP v prvej minúte
    rows = [(m, 100.0 + m, 101.0 + m, 100.0 + m, 101.0 + m) for m in range(-120, 120)]
    cfg_ = IBSConfig(maxDailyWins=2)
    result, runner = emulate(cfg_, MNQ, m1_frame(rows), 3, spec=_spy_spec(_EveryBarLong))
    per_day: dict[int, int] = {}
    for t in result.trades:
        assert t.reason == "take_profit"
        per_day[_day(t.open_ms)] = per_day.get(_day(t.open_ms), 0) + 1
    d0, d1 = _day(T0 - MIN), _day(T0)
    # Pine: výhra z baru blokuje až od ďalšieho baru, takže limit 2 pustí ešte jeden rozbehnutý vstup
    assert per_day[d0] == 3 and per_day[d1] == 3
    limits = runner.engine.limits
    assert any(flag for ts, flag in limits if _day(ts) == d0)
    first_new_day = next(flag for ts, flag in limits if _day(ts) == d1)
    assert first_new_day is False

    unlimited, _ = emulate(IBSConfig(maxDailyWins=20), MNQ, m1_frame(rows), 3, spec=_spy_spec(_EveryBarLong))
    assert len(unlimited.trades) > len(result.trades)


def test_max_daily_wins_straty_ani_vyhra_zjedena_poplatkom_sa_nepocitaju():
    class Losing(_EveryBarLong):
        tp = 100.0
        sl = 0.5

    falling = [(m, 300.0 - m, 300.0 - m, 299.0 - m, 299.0 - m) for m in range(0, 120)]
    result, runner = emulate(IBSConfig(maxDailyWins=1), MNQ, m1_frame(falling), 3, spec=_spy_spec(Losing))
    assert len(result.trades) > 5 and all(t.reason == "stop_loss" for t in result.trades)
    assert not any(flag for _ts, flag in runner.engine.limits)

    class TinyWin(_EveryBarLong):
        tp = 0.01  # hrubý zisk 0.01 bodu, poplatok ~100 * 2 * 0.001 -> po poplatku strata

    rising = [(m, 100.0 + m, 101.0 + m, 100.0 + m, 101.0 + m) for m in range(0, 60)]
    result, runner = emulate(IBSConfig(maxDailyWins=1), MNQ, m1_frame(rising), 3, spec=_spy_spec(TinyWin), fee=0.001)
    assert len(result.trades) > 5 and not any(flag for _ts, flag in runner.engine.limits)
