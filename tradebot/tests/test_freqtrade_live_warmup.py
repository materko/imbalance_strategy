"""Predhistória v dry-run a live (`TradebotStrategyBase._seed_runner`, `informative_pairs`).

Freqtrade v dry/live dá stratégii DataFrame od burzy (aspoň `startup_candle_count + 1`
sviečok) a informatívne TF, ktoré si stratégia vypýta. Adaptér z toho musí dostať ten istý
stav ako backtest: runner prejde predhistóriu grafu, indikátory na vlastnom TF sa seedujú
z uzavretých barov pred prvým spracovaným barom (od DataProvidera, inak zo sviečok TF behu
stiahnutých z burzy) a signál z baru bez celej predhistórie vstup neurobí.

Bez siete: DataProvider aj burza sú falošné a sviečky sú poskladané z tých istých 1m dát
ako súbory pre backtest.
"""

from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("freqtrade")

from freqtrade.data.history import get_datahandler
from freqtrade.enums import CandleType, RunMode

from tradebot.adapters.freqtrade.runner import EngineRunner
from tradebot.core.candles import resample_ohlcv, timeframe_minutes, timeframe_name
from tradebot.strategies import get_spec
from tradebot.tests.test_warmup import HOUR, MIN, T_START, _ibs_strategy, _m1, _state

PAIR = "BTC/USDT:USDT"
DAY = 24 * HOUR
#: ako Binance: jedno volanie = 500 sviečok, Freqtrade ich pri štarte stiahne toľko
LIMIT = 500


def _ms(frame) -> pd.Series:
    return frame["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000


def _closed(base, minutes: int, now_ms: int, limit: int | None = LIMIT):
    """Uzavreté sviečky TF `minutes` pred `now_ms`, posledných `limit` — čo má burza v cache."""
    frame = resample_ohlcv(base, minutes)
    frame = frame[_ms(frame) + minutes * MIN <= now_ms].reset_index(drop=True)
    return frame.tail(limit).reset_index(drop=True) if limit else frame


class FakeExchange:
    """`timeframes` a `get_historic_ohlcv` ako Freqtrade `Exchange` — bez siete.

    História vracia aj sviečky za `until_ms`, a to so zmenenými cenami: adaptér ich musí
    odrezať sám, inak by seeding videl budúcnosť.
    """

    def __init__(self, base, now_ms: int, timeframes: list[str]) -> None:
        self.base, self.now_ms, self.timeframes = base, now_ms, list(timeframes)
        self.calls: list[tuple[str, int, int | None]] = []

    def get_historic_ohlcv(self, pair, timeframe, since_ms, candle_type, is_new_pair=False, until_ms=None):
        self.calls.append((timeframe, since_ms, until_ms))
        frame = _closed(self.base, timeframe_minutes(timeframe), self.now_ms, limit=None)
        frame = frame[_ms(frame) >= since_ms].reset_index(drop=True)
        future = (_ms(frame) >= (until_ms or self.now_ms)).to_numpy()
        for col in ("open", "high", "low", "close"):
            frame.loc[future, col] = frame.loc[future, col] * 1.5 + 999.0
        return frame


class FakeDP:
    """To, čo z DataProvidera adaptér používa: whitelist, sviečky TF a burza za ním."""

    def __init__(self, exchange: FakeExchange | None, frames: dict[str, pd.DataFrame], runmode: RunMode):
        self._exchange, self.frames, self.runmode = exchange, frames, runmode

    def current_whitelist(self):
        return [PAIR]

    def get_pair_dataframe(self, pair, timeframe=None, candle_type=""):
        frame = self.frames.get(timeframe)
        return frame.copy() if frame is not None else pd.DataFrame()

    def historic_ohlcv(self, pair, timeframe, candle_type=""):
        return self.get_pair_dataframe(pair, timeframe)


def _live_dp(base, now_ms: int, timeframes: list[str], runmode=RunMode.DRY_RUN, alter_from: int | None = None):
    exchange = FakeExchange(base, now_ms, timeframes)
    frames = {tf: _closed(base, timeframe_minutes(tf), now_ms) for tf in timeframes}
    if alter_from is not None:
        for frame in frames.values():
            later = (_ms(frame) >= alter_from).to_numpy()
            frame.loc[later, ["open", "high", "low", "close"]] = frame.loc[later, ["open", "high", "low", "close"]] * 1.3 + 77.0
    return FakeDP(exchange, frames, runmode)


def _datadir(tmp_path, base, chart: int):
    datadir = tmp_path / "data"
    (datadir / "futures").mkdir(parents=True, exist_ok=True)
    get_datahandler(datadir, "feather").ohlcv_store(PAIR, f"{chart}m", data=resample_ohlcv(base, chart),
                                                     candle_type=CandleType.FUTURES)
    return datadir


IND = dict(indSupertrend=True, indAdx=True, stTimeframe="60", adxTimeframe="60")
TFS = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]


def _ibs(tmp_path, monkeypatch, runmode, dp, datadir=None, **fields):
    extra = {"runmode": runmode, "candle_type_def": CandleType.FUTURES}
    if datadir is not None:
        extra.update(datadir=str(datadir), dataformat_ohlcv="feather")
    s = _ibs_strategy(tmp_path, monkeypatch, "3m", config_extra=extra, **{**IND, **fields})
    s.dp = dp
    return s


def _backtest_twin(tmp_path, monkeypatch, base, df, now_ms, **fields):
    """Backtest tých istých barov: DataFrame od prvého baru live runnera, predhistória z disku."""
    dp = FakeDP(None, {"5m": _closed(base, 5, now_ms, limit=None)}, RunMode.BACKTEST)
    s = _ibs(tmp_path, monkeypatch, RunMode.BACKTEST, dp, datadir=_datadir(tmp_path, base, 3), **fields)
    out = s.populate_indicators(df.reset_index(drop=True).copy(), {"pair": PAIR})
    return s, s._runners[PAIR], out


@pytest.fixture(scope="module")
def m1():
    # 20 dní 1m s dvojhodinovou dierou v dátach tam, kam siaha seeding ADX
    return _m1(20, seed=5, gap=(12 * 1440 + 300, 120))


# --------------------------------------------------------------------------- #


def test_informative_pairs_pytaju_tf_indikatorov(tmp_path, monkeypatch, m1):
    now = T_START + 16 * DAY
    s = _ibs(tmp_path, monkeypatch, RunMode.LIVE, _live_dp(m1, now, TFS), adxTimeframe="120")
    pairs = s.informative_pairs()
    assert (PAIR, "5m") in pairs and (PAIR, "1h") in pairs     # detekčný TF zón + Supertrend 60m
    assert (PAIR, "2h") not in pairs                              # burza 2h nepozná -> z TF behu
    s.dp = _live_dp(m1, now, TFS + ["2h"])
    assert (PAIR, "2h") in s.informative_pairs()
    assert timeframe_name(60) == "1h" and timeframe_name(1440) == "1d" and timeframe_name(90) == "90m"


@pytest.mark.parametrize("runmode", [RunMode.DRY_RUN, RunMode.LIVE])
def test_live_stav_na_prvom_obchodovatelnom_bare_je_ako_backtest(tmp_path, monkeypatch, m1, runmode):
    now = T_START + 16 * DAY + 7 * HOUR + 21 * MIN
    window = _closed(m1, 3, now)
    ts = _ms(window).tolist()
    startup = 300
    k = next(i for i, t in enumerate(ts) if t % HOUR == 0)
    live_df = window.iloc[: k + startup + 1].reset_index(drop=True)   # posledný riadok = prvý obchodovateľný
    dp = _live_dp(m1, ts[k + startup] + 3 * MIN, TFS, runmode)
    s = _ibs(tmp_path, monkeypatch, runmode, dp)
    assert s.startup_candle_count == startup
    out = s.populate_indicators(live_df.copy(), {"pair": PAIR})
    live = s._runners[PAIR]

    assert live.first_ts == ts[k] and live.processed == startup + 1
    assert live.ready_ts == ts[k + startup] == live.last_ts
    assert dp._exchange.calls == []                    # zarovnaný štart, 1h od DataProvidera stačí
    gate = live.engine.direction_gate
    assert gate.st.warmed and gate.dmi.warmed and gate.states is not None

    _, bt, bt_out = _backtest_twin(tmp_path, monkeypatch, m1, window.iloc[k: k + startup + 1], now)
    assert bt.first_ts == live.first_ts and bt.last_ts == live.last_ts
    assert _state(gate) == _state(bt.engine.direction_gate)
    # riadky pred štartom runnera a predhistória nesú nula signálov; prvý obchodovateľný ako backtest
    assert (out.loc[: k + startup - 1, ["tb_enter_long", "tb_enter_short"]] == 0).all().all()
    for col in ("tb_enter_long", "tb_enter_short", "tb_entry"):
        a, b = out[col].iloc[-1], bt_out[col].iloc[-1]
        assert a == b or (a != a and b != b)


def test_live_seeding_neberie_bary_od_prveho_baru(tmp_path, monkeypatch, m1):
    """Sviečky TF indikátora od prvého baru runnera ďalej (zmenené) stav nezmenia."""
    now = T_START + 16 * DAY + 7 * HOUR + 21 * MIN
    window = _closed(m1, 3, now)
    ts = _ms(window).tolist()
    k = next(i for i, t in enumerate(ts) if t % HOUR == 0)
    states = []
    for alter in (None, ts[k]):
        s = _ibs(tmp_path, monkeypatch, RunMode.DRY_RUN, _live_dp(m1, now, TFS, alter_from=alter))
        s.populate_indicators(window.copy(), {"pair": PAIR})
        states.append(_state(s._runners[PAIR].engine.direction_gate))
    assert states[0] == states[1]
    # kontrola testu: zmena pred prvým barom stav zmení
    s = _ibs(tmp_path, monkeypatch, RunMode.DRY_RUN, _live_dp(m1, now, TFS, alter_from=ts[k] - 6 * HOUR))
    s.populate_indicators(window.copy(), {"pair": PAIR})
    assert _state(s._runners[PAIR].engine.direction_gate) != states[0]


def test_live_tf_mimo_burzy_a_nezarovnany_start_z_historie_tf_behu(tmp_path, monkeypatch, m1):
    """ADX 2h burza nemá a za zarovnaným riadkom by neostala predhistória: uzavreté 2h bary
    aj rozpracované periódy sa poskladajú zo sviečok TF behu stiahnutých z burzy — len pred
    prvým barom, hoci burza vráti aj neskoršie (so zmenenými cenami)."""
    boundary = T_START + 16 * DAY + 6 * HOUR                  # násobok 2h
    first = boundary + 3 * 3 * MIN                             # 3 bary za hranicou 2h
    rows = 310
    now = first + rows * 3 * MIN
    window = _closed(m1, 3, now, limit=rows)
    assert _ms(window).iloc[0] == first
    dp = _live_dp(m1, now, TFS)
    s = _ibs(tmp_path, monkeypatch, RunMode.LIVE, dp, adxTimeframe="120")
    s.populate_indicators(window.copy(), {"pair": PAIR})
    live = s._runners[PAIR]
    assert live.first_ts == first                                # zarovnať sa nedalo
    assert dp._exchange.calls and all(tf == "3m" and until <= first for tf, _, until in dp._exchange.calls)

    _, bt, _ = _backtest_twin(tmp_path, monkeypatch, m1, window, now, adxTimeframe="120")
    gate = live.engine.direction_gate
    assert gate.dmi.warmed and gate.st.warmed
    assert _state(gate) == _state(bt.engine.direction_gate)


def test_live_bez_celej_predhistorie_nevstupuje(tmp_path, monkeypatch, m1):
    """Krátky DataFrame (nový pár) a živá slučka po jednej sviečke: vstup až po 300 baroch."""
    original = EngineRunner.process

    def always_long(self, bar, htf=None):
        row = original(self, bar, htf)
        row.enter_long, row.entry, row.stop_loss, row.take_profit, row.qty = 1, bar.close, bar.low, bar.high, 1.0
        return row

    monkeypatch.setattr(EngineRunner, "process", always_long)
    now = T_START + 16 * DAY
    window = _closed(m1, 3, now, limit=330)
    s = _ibs(tmp_path, monkeypatch, RunMode.DRY_RUN, _live_dp(m1, now, TFS))
    for n in range(200, 331):
        df = s.populate_indicators(window.iloc[:n].reset_index(drop=True).copy(), {"pair": PAIR})
        df = s.populate_entry_trend(df, {"pair": PAIR})
        runner = s._runners[PAIR]
        assert runner.first_ts == _ms(window).iloc[0]            # krátky DataFrame: bez zarovnania
        entries = (df["enter_long"] == 1).to_numpy() if "enter_long" in df else [False] * n
        assert list(entries) == [i >= 300 for i in range(n)]
    assert runner.processed == 330


def test_restart_a_diera_seeduju_nanovo(tmp_path, monkeypatch, m1):
    now1 = T_START + 15 * DAY + 5 * HOUR + 9 * MIN
    now2 = now1 + 2 * HOUR
    now3 = now2 + 3 * DAY
    a = _ibs(tmp_path, monkeypatch, RunMode.LIVE, _live_dp(m1, now1, TFS))
    a.populate_indicators(_closed(m1, 3, now1).copy(), {"pair": PAIR})
    first_a = a._runners[PAIR].first_ts
    w2 = _closed(m1, 3, now2)
    a.dp = _live_dp(m1, now2, TFS)
    a.populate_indicators(w2.copy(), {"pair": PAIR})             # bežná slučka: nadväzuje
    assert a._runners[PAIR].first_ts == first_a and a._runners[PAIR].last_ts == _ms(w2).iloc[-1]

    # reštart botu: nová inštancia, DataFrame od burzy znova
    b = _ibs(tmp_path, monkeypatch, RunMode.LIVE, _live_dp(m1, now2, TFS))
    b.populate_indicators(w2.copy(), {"pair": PAIR})
    rb = b._runners[PAIR]
    assert rb.first_ts != first_a and rb.first_ts % HOUR == 0
    k = _ms(w2).tolist().index(rb.first_ts)
    _, bt, _ = _backtest_twin(tmp_path, monkeypatch, m1, w2.iloc[k:], now2)
    ga, gb = a._runners[PAIR].engine.direction_gate, rb.engine.direction_gate
    assert _state(gb) == _state(bt.engine.direction_gate)
    assert gb.states == ga.states and gb.st.trend == ga.st.trend

    # výpadok: sviečky po troch dňoch nenadväzujú -> runner nanovo, ako čerstvý štart
    w3 = _closed(m1, 3, now3)
    a.dp = _live_dp(m1, now3, TFS)
    a.populate_indicators(w3.copy(), {"pair": PAIR})
    c = _ibs(tmp_path, monkeypatch, RunMode.LIVE, _live_dp(m1, now3, TFS))
    c.populate_indicators(w3.copy(), {"pair": PAIR})
    ra, rc = a._runners[PAIR], c._runners[PAIR]
    assert ra.first_ts == rc.first_ts > _ms(w3).iloc[0] - 1 and ra.processed == rc.processed
    assert _state(ra.engine.direction_gate) == _state(rc.engine.direction_gate)


def test_divergencia_live_ako_backtest(tmp_path, monkeypatch):
    from tradebot.strategies.divergence.freqtrade import DivergenceStrategy

    m15 = resample_ohlcv(_m1(70, seed=3), 15)
    now = T_START + 69 * DAY + 13 * HOUR
    window = _closed(m15, 15, now)
    tfs = ["15m", "1h", "4h"]
    config = {"timeframe": "15m", "exchange": {"pair_whitelist": [], "name": "binance"},
              "stake_currency": "USDT", "dry_run": True, "trading_mode": "futures",
              "margin_mode": "isolated", "candle_type_def": CandleType.FUTURES}
    monkeypatch.delenv("TRADEBOT_PROFILE", raising=False)
    live = DivergenceStrategy({**config, "runmode": RunMode.DRY_RUN})
    live.dp = _live_dp(m15, now, tfs)
    assert {(PAIR, "1h"), (PAIR, "4h")} <= set(live.informative_pairs())
    live.populate_indicators(window.copy(), {"pair": PAIR})
    rl = live._runners[PAIR]
    assert rl.first_ts % (4 * HOUR) == 0 and live.dp._exchange.calls == []
    k = _ms(window).tolist().index(rl.first_ts)

    bt = DivergenceStrategy({**config, "runmode": RunMode.BACKTEST,
                             "datadir": str(_datadir(tmp_path, m15, 15)), "dataformat_ohlcv": "feather"})
    bt.dp = None
    bt.populate_indicators(window.iloc[k:].reset_index(drop=True).copy(), {"pair": PAIR})
    rb = bt._runners[PAIR]
    for x, y in ((rl.engine.htf1, rb.engine.htf1), (rl.engine.htf2, rb.engine.htf2)):
        assert x.bars >= x.warmup_bars
        assert (x.st.trend, x.st.line, x.bull, x.bear, list(x.window)) == \
               (y.st.trend, y.st.line, y.bull, y.bear, list(y.window))
        assert (x.agg._open_ts, x.agg._c) == (y.agg._open_ts, y.agg._c)
