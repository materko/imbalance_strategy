"""Natívny C# backtest (`tradebot/csharp/TradeBot.Backtest/McEmulator.cs`) = Python emulátor MultiCharts, obchod po obchode.

C# strana nepoužije nič z Pythonu: feather číta sama, TF skladá sama (`CandleOps` = `resample_ohlcv`),
seeduje predhistóriu (`seed_engine`), kŕmi HTF feeder a emuluje brokera (`MCRunner` + `emulate`). Keby sa
čokoľvek z toho rozišlo, hyperopt v C# by optimalizoval inú stratégiu, než akú webapp ukazuje.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tradebot.core.candles import timeframe_minutes
from tradebot.core.types import INSTRUMENTS
from tradebot.strategies import get_spec
from tester import engines
from tester.compare.csharp_backtest import compare_trades, run_csharp, run_python


def _ms(day: str) -> int:
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


#: (stratégia, profil, inštrument, od, do, --set) — každá C# stratégia, HTF + seeding (IBS), EOD obal,
#: trailing a denný limit výhier. Krátke okná: celé roky prechádza CLI `tester.compare.csharp_backtest`.
CASES = [
    ("ibsnet", None, "btcusdt_binance", "2026-06-01", "2026-08-01", {}),
    ("ibsnet", None, "btcusdt_binance", "2026-02-01", "2026-04-01",
     {"enableTrailing": True, "rrRatio": 3, "trailActivationR": 1, "trailOffsetR": 0.5, "maxDailyWins": 1}),
    ("ibsentrynet", None, "btcusdt_binance", "2026-06-01", "2026-08-01", {}),
    ("ibsnet", "multicharts_mnq_3m", "mnq_databento", "2025-01-01", "2025-03-01", {}),
    ("orbnet", None, "nas100_dukascopy", "2025-01-01", "2025-03-01", {}),
    ("vwaporbnet", None, "mnq_databento", "2025-01-01", "2025-03-01", {}),
    ("vwaporbneteod", None, "mnq_databento", "2025-01-01", "2025-03-01", {}),
    ("vwapadxnet", None, "mnq_databento", "2025-01-01", "2025-02-01", {}),
    ("noanet", None, "mnq_databento", "2025-01-01", "2025-03-01", {}),
    ("tksnet", None, "mnq_databento", "2025-01-01", "2025-03-01", {}),
    ("tksneteod", None, "mnq_databento", "2025-01-01", "2025-03-01", {}),
    # audit N-CS-6: každá C# stratégia aj EOD kópia, nie len pôvodná sada
    ("ibsentryneteod", "multicharts_mnq_3m", "mnq_databento", "2025-01-01", "2025-03-01", {}),
    ("noaneteod", None, "mnq_databento", "2025-01-01", "2025-03-01", {}),
    ("vwapadxneteod", None, "mnq_databento", "2025-01-01", "2025-02-01", {}),
    ("ibsentryesnet", None, "es_databento", "2025-01-01", "2025-03-01", {}),
    ("nyvaesnet", None, "es_databento", "2025-01-01", "2025-03-01", {}),
    ("fibomgcnet", None, "mgc_databento", "2025-01-01", "2025-03-01", {}),
    ("sdeurnet", None, "6e_databento", "2025-01-01", "2025-03-01", {}),
]


@pytest.fixture(scope="module", autouse=True)
def _clr():
    from tradebot.adapters.csharp import bridge

    try:
        bridge._load_clr()
    except bridge.BridgeError as exc:
        pytest.skip(f"pythonnet/CLR nie je k dispozícii: {exc}")


@pytest.mark.parametrize("strategy,profile,inst_key,day_from,day_to,sets", CASES,
                         ids=[f"{c[0]}-{c[2]}" + ("-set" if c[5] else "") for c in CASES])
def test_native_matches_python_emulator(strategy, profile, inst_key, day_from, day_to, sets):
    inst = INSTRUMENTS[inst_key]
    if not engines.one_minute_file(inst).exists():
        pytest.skip(f"chýbajú 1m dáta {engines.one_minute_file(inst)}")
    tf = timeframe_minutes(get_spec(strategy).default_timeframe)
    args = (strategy, profile, inst, tf, _ms(day_from), _ms(day_to), 0.0005, sets)
    py = run_python(*args)
    cs = run_csharp(*args)
    assert py, "okno bez obchodov nič neoverí — zvoľ iné"
    assert compare_trades(py, cs["trades"]) == []
    if sets.get("enableTrailing"):
        assert any(t["reason"] == "trailing_stop" for t in py), "trailing sa v okne neprejavil"


@pytest.mark.parametrize("minutes", [3, 5, 15, 60, 240, 1440, 10080])
def test_resample_matches_pandas(minutes):
    """`CandleOps.Resample` = `resample_ohlcv` na bit — aj s dierami, NaN a týždňom od pondelka."""
    import numpy as np
    import pandas as pd
    from System import Array, Double, Int64
    from TradeBot.Backtest import CandleOps, Candles

    from tradebot.core.candles import resample_ohlcv

    rng = np.random.default_rng(minutes)
    n = 40_000
    t = 1_600_000_000_000 // 60_000 * 60_000 + 60_000 * np.cumsum(rng.integers(1, 4, n))   # diery v dátach
    df = pd.DataFrame({"date": pd.to_datetime(t, unit="ms", utc=True),
                       "open": rng.normal(100, 1, n), "high": rng.normal(101, 1, n), "low": rng.normal(99, 1, n),
                       "close": rng.normal(100, 1, n), "volume": rng.random(n) * 10.0 ** rng.integers(-3, 6, n)})
    df.loc[rng.random(n) < 0.02, ["open", "volume"]] = np.nan
    c = Candles()
    c.Time = Array[Int64]([int(x) for x in t])
    for name in ("open", "high", "low", "close", "volume"):
        setattr(c, name.capitalize(), Array[Double](df[name].tolist()))
    got = CandleOps.Resample(c, minutes)
    want = resample_ohlcv(df, minutes)
    assert got.Count == len(want)
    want_t = (want["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000).tolist()
    assert list(got.Time) == want_t
    for name in ("open", "high", "low", "close", "volume"):
        a = np.array(list(getattr(got, name.capitalize())))
        b = want[name].to_numpy(np.float64)
        nan = np.isnan(b)
        assert np.array_equal(np.isnan(a), nan), name
        assert np.array_equal(a[~nan].view(np.int64), b[~nan].view(np.int64)), name


def test_register_enginov_sa_po_nacitani_assembly_obnovi():
    """NinjaTrader po rekompilácii načíta novú generáciu assembly a stará ostane v AppDomain — register sa
    musí zabudnúť sám, nie až po ručnom `Reset()` (audit N-CS-3); duplicitné kľúče vie vymenovať."""
    import System
    from TradeBot.Core import EngineRegistry

    known = EngineRegistry.Known()
    assert known.ContainsKey("ibsnet") and list(EngineRegistry.Duplicates()) == []
    assert System.Object.ReferenceEquals(EngineRegistry.Known(), known)       # bez novej assembly cache drží
    System.Reflection.Assembly.Load("System.Data.OracleClient, Version=4.0.0.0, Culture=neutral, "
                                    "PublicKeyToken=b77a5c561934e089")     # nová assembly v AppDomain
    assert not System.Object.ReferenceEquals(EngineRegistry.Known(), known)
