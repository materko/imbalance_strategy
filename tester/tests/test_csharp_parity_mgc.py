"""Fibo 1.0 MGC s C# jadrom (`fibomgcnet`) proti Python predlohe (`fibomgc`) — bar po bare, na rovnosť.

Syntetické bary s viacerými variantmi (vrátane stropu straty `skipOverRisk`, ktorý časť vstupov vynechá) a všetkých
desať profilov, ktoré prešli smernicou, na MGC (keď sú sviečky v sklade). Bez C# kompilátora (csc / Mono) sa preskočí.
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
from tradebot.strategies.fibomgcnet import CONFIG_DIR  # noqa: E402

PROFILE_1 = CONFIG_DIR / "PRESIEL_SMERNICAMI_Fibo_1_0_MGC_1.json"

VARIANTS = {
    "profil_1": {},
    "pullback_rr_urovne": {"slMode": "pullback", "tpMode": "rr", "rrRatio": 1.2, "levelMode": "levels", "entryModel": "any",
                           "levelTolAtr": {"value": 1.0, "unit": "atr"}},
    "okno_drzanie_bez_vikendov": {"useTradeWindow": True, "tradeStartH": 8, "tradeEndH": 12, "maxHoldBars": 20,
                                  "weekdaysOnly": True, "maxTradesPerDay": 1, "requireBreak": False},
    "strop_straty_skipOverRisk": {"skipOverRisk": True, "riskDollar": 100.0},   # 2 z 9 vstupov, zvyšok strop vynechá
    "pevny_pocet": {"fixedQty": True, "qty": 2.0, "imbMinSizeAtr": {"value": 0.0, "unit": "atr"}},
}


def _walk(days: int, seed: int = 5) -> pd.DataFrame:
    """1m sviečky zlata (tick 0,1) od 20. 10. 2026 — cez zmenu času v Európe aj v USA."""
    rng = random.Random(seed)
    rows, price = [], 2400.0
    t0 = pd.Timestamp("2026-10-20 00:00", tz="UTC")
    for i in range(days * 1440):
        op = round(price + rng.choice((0.0, 0.0, 0.0, rng.uniform(-1.5, 1.5))), 1)
        close = round(op + rng.gauss(0, 0.9), 1)
        high = round(max(op, close) + abs(rng.gauss(0, 0.4)), 1)
        low = round(min(op, close) - abs(rng.gauss(0, 0.4)), 1)
        rows.append((t0 + pd.Timedelta(minutes=i), op, high, low, close, round(rng.uniform(5, 400), 1)))
        price = close
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


@pytest.fixture(scope="module")
def frames():
    base = _walk(16)
    return {m: _with_ts(base if m == 1 else resample_ohlcv(base, m)) for m in (1, 3, 5, 6, 15, 60)}


def _plain(path: Path, tmp_path: Path) -> Path:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_strategy", None)          # ten istý profil pre predlohu aj C# port
    out = tmp_path / path.name
    out.write_text(json.dumps(data), encoding="utf-8")
    return out


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_fibo_synteticke_bary(frames, name, tmp_path):
    res = csharp_parity.compare_frames(
        "fibomgc", "fibomgcnet", str(_plain(PROFILE_1, tmp_path)), frames[3], lambda tf: frames[int(tf.rstrip("m"))], 3,
        None, None, VARIANTS[name], 10,
    )
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 0, res["counts"]


@pytest.mark.parametrize("path", sorted(CONFIG_DIR.glob("PRESIEL_SMERNICAMI_Fibo_1_0_MGC_*.json")), ids=lambda p: p.stem)
def test_fibo_presle_profily_na_mgc(path, tmp_path):
    try:
        res = csharp_parity.compare("fibomgc", "fibomgcnet", str(_plain(path, tmp_path)), "mgc", 3, "2026-03-01", "2026-06-01")
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
