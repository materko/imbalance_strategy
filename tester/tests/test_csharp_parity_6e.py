"""SD ZÓNY EURUSD s C# jadrom (`sdeurnet`) proti Python predlohe `sdeur` — bar po bare, na rovnosť.

Varianty na syntetických baroch cez zmenu času v Európe (25. 10.) aj v USA (1. 11.) a na skutočnom 6E
(keď sú sviečky v sklade), vrátane stropu straty `skipOverRisk` s rizikom, pri ktorom časť vstupov vypadne.
Bez C# kompilátora (csc / Mono) sa preskočí.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd
import pytest

from tradebot.adapters.csharp import build as csbuild

try:
    csbuild.ensure_built()
except csbuild.BuildError as exc:  # pragma: no cover - stroj bez C# kompilátora
    pytest.skip(f"C# jadro sa nedá preložiť: {exc}", allow_module_level=True)

from tester.compare import csharp_parity  # noqa: E402
from tester.tests.test_csharp_parity import _with_ts  # noqa: E402
from tradebot.core.candles import resample_ohlcv  # noqa: E402
from tradebot.strategies.sdeurnet import CONFIG_DIR  # noqa: E402

PROFILE = CONFIG_DIR / "eurusd_6e_5m.json"

VARIANTS = {
    "profil": {},
    "hlbka_50_limit_dna": {"entryDepthPct": 50.0, "maxTradesPerDay": 1, "rrRatio": 2.0},
    "bez_okna_vzniku_15m": {"useFormWindow": False, "zoneTF": 15, "depMaxBars": 4, "extremeBars": 0},
    "vyska_v_tickoch_drzanie": {"minZoneHeight": {"value": 8, "unit": "ticks"},
                                "maxZoneHeight": {"value": 60, "unit": "ticks"}, "maxHoldHours": 6,
                                "entryStartH": 20, "entryEndH": 11},
    "strop_straty_skipOverRisk": {"skipOverRisk": True, "riskDollar": 150.0, "fixedQty": True, "qty": 1.0},
    "len_long_trend": {"allowShort": False, "trendFilter": "with", "trendEmaLen": 50},
}


def _walk(days: int, seed: int = 7) -> pd.DataFrame:
    """1m sviečky od 20. 10. 2026 — cez zmenu času v Európe (25. 10.) aj v USA (1. 11.), tick 0,00005."""
    rng = random.Random(seed)
    rows, price = [], 1.1000
    t0 = pd.Timestamp("2026-10-20 00:00", tz="UTC")
    tick = 0.00005
    for i in range(days * 1440):
        op = round((price + rng.choice((0.0, 0.0, 0.0, rng.uniform(-0.0004, 0.0004)))) / tick) * tick
        close = round((op + rng.gauss(0, 0.00018)) / tick) * tick
        high = max(op, close) + round(abs(rng.gauss(0, 0.0001)) / tick) * tick
        low = min(op, close) - round(abs(rng.gauss(0, 0.0001)) / tick) * tick
        rows.append((t0 + pd.Timedelta(minutes=i), op, high, low, close, round(rng.uniform(10, 900), 1)))
        price = close
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


@pytest.fixture(scope="module")
def frames():
    base = _walk(16)
    return {m: _with_ts(base if m == 1 else resample_ohlcv(base, m)) for m in (1, 5, 15, 60)}


def _plain(path: Path, tmp_path: Path) -> Path:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_strategy", None)          # ten istý profil pre predlohu aj C# port
    out = tmp_path / path.name
    out.write_text(json.dumps(data), encoding="utf-8")
    return out


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_synteticke_bary_cez_zmenu_casu(frames, name, tmp_path):
    res = csharp_parity.compare_frames(
        "sdeur", "sdeurnet", str(_plain(PROFILE, tmp_path)), frames[5], lambda tf: frames[int(tf.rstrip("m"))], 5,
        None, None, VARIANTS[name], 10,
    )
    assert res["mismatches"] == [], res["mismatches"][:3]


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_na_6e(name, tmp_path):
    try:
        res = csharp_parity.compare("sdeur", "sdeurnet", str(_plain(PROFILE, tmp_path)), "6e", 5,
                                    "2026-01-01", "2026-05-01", VARIANTS[name])
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["drawings"] > 50, res["counts"]
