"""IBSNet (C# jadro) proti IBS (Python) — bar po bare, na rovnosť.

C# jadro je prepis, nie nová stratégia: na rovnakých vstupoch musí dať rovnaké ordery, kresby,
udalosti aj hodiny seáns, do posledného bitu. Syntetický test beží vždy (nepotrebuje dáta),
test na golden okne len keď sú v sklade sviečky. Bez C# kompilátora (csc / Mono) sa preskočí.
"""

from __future__ import annotations

import random

import pandas as pd
import pytest

from tradebot.adapters.csharp import build as csbuild

try:
    csbuild.ensure_built()
except csbuild.BuildError as exc:  # pragma: no cover - stroj bez C# kompilátora
    pytest.skip(f"C# jadro sa nedá preložiť: {exc}", allow_module_level=True)

from tester.compare import csharp_parity  # noqa: E402
from tradebot.core.candles import resample_ohlcv  # noqa: E402

#: Všetko zapnuté a prahy povolené tak, aby sa na náhodnej prechádzke naozaj niečo dialo:
#: zóny zo všetkých troch zdrojov, tri entry modely, trailing, smer podľa Supertrendu aj ADX.
AGGRESSIVE = {
    "sess1On": True, "sess2On": True, "sess3On": True, "weekdaysOnly": False,
    "sess1ZoneStartH": 0, "sess1ZoneEndH": 23, "sess1TradeStartH": 0, "sess1TradeEndH": 22,
    "enablePinBarEntry": True, "enableEngulfingEntry": True, "enableSrTrading": True, "enableLqTrading": True,
    "showElliott": True, "enableTrailing": True, "rrRatio": 3.0, "useVolumeFilter": True,
    "tradeDirection": "Indicator", "indSupertrend": True, "indAdx": True, "stTimeframe": "15", "adxTimeframe": "15",
    "legacyPineSizing": False, "maxDailyWins": 2, "state3MaxBars": 5,
}


def _random_walk(bars: int, seed: int = 7) -> pd.DataFrame:
    """1m sviečky s gapmi a knôtmi — deterministické (pevný seed), ceny na tick 0,1."""
    rng = random.Random(seed)
    rows, price = [], 50_000.0
    t0 = pd.Timestamp("2026-03-27 00:00", tz="UTC")  # cez jarný posun času v Európe (29. 3.)
    for i in range(bars):
        op = round(price + rng.choice((0.0, 0.0, 0.0, rng.uniform(-25, 25))), 1)  # občas gap
        close = round(op + rng.gauss(0, 12), 1)
        high = round(max(op, close) + abs(rng.gauss(0, 6)), 1)
        low = round(min(op, close) - abs(rng.gauss(0, 6)), 1)
        rows.append((t0 + pd.Timedelta(minutes=i), op, high, low, close, round(rng.uniform(1, 50), 3)))
        price = close
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


def _with_ts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ts"] = df["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000
    return df


@pytest.fixture(scope="module")
def frames():
    base = _random_walk(6 * 1440)
    return {m: _with_ts(base if m == 1 else resample_ohlcv(base, m)) for m in (1, 3, 5)}


def _run(frames, overrides, monkeypatch=None, bridge=None):
    if bridge is not None:
        monkeypatch.setenv("TRADEBOT_CSHARP_BRIDGE", bridge)
    return csharp_parity.compare_frames(
        "ibs", "ibsnet", "golden_binance_btcusdt_3m", frames[3], lambda tf: frames[int(tf.rstrip("m"))], 3,
        "2026-03-28", None, overrides, 10,
    )


def test_synteticke_bary_vsetko_zapnute(frames):
    res = _run(frames, AGGRESSIVE)
    assert res["mismatches"] == [], res["mismatches"][:3]
    c = res["counts"]
    # bez toho by zhoda nič neznamenala: test musí naozaj prejsť vstupmi, stavmi aj kresbami
    assert c["entries"] > 0 and c["events"] > 100 and c["drawings"] > 1000, c
    assert res["seeded"]["ibs"] == res["seeded"]["ibsnet"] != {}


def test_synteticke_bary_pine_defaulty(frames):
    res = _run(frames, {})
    assert res["mismatches"] == [], res["mismatches"][:3]


def test_stdio_transport_dava_to_iste(frames, monkeypatch):
    """Samostatný proces (`TradeBot.Host.exe`) musí dať to isté čo pythonnet — čísla idú ako bity."""
    res = _run(frames, AGGRESSIVE, monkeypatch, "stdio")
    assert res["mismatches"] == [], res["mismatches"][:3]


def test_golden_okno_binance():
    try:
        res = csharp_parity.compare("ibs", "ibsnet", "golden_binance_btcusdt_3m", "binance", 3,
                                    "2026-08-24", "2026-09-04")
    except SystemExit as exc:  # chýbajúce feather dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 0


def test_engine_prezije_pickle_pre_hyperopt():
    """Hyperopt posiela stratégiu aj s enginmi do paralelných procesov cez pickle; C# objekt
    sa preniesť nedá, engine sa na druhej strane otvorí nanovo s tým istým configom."""
    import pickle

    from tradebot.core import load_profile
    from tradebot.strategies import get_spec

    cfg, inst = load_profile("golden_binance_btcusdt_3m", strategy="ibsnet")
    engine = get_spec("ibsnet").engine_factory(cfg, inst, 3)
    clone = pickle.loads(pickle.dumps(engine))
    assert clone.required_history == engine.required_history
    assert clone.warmup.describe() == engine.warmup.describe()
    assert clone.stats()["zones"] == 0
