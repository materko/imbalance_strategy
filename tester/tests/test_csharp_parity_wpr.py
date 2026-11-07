"""WILLIAMS %R LONG s C# jadrom (`wprnet`) proti Python predlohe (`wpr`) — bar po bare, na rovnosť.

Syntetické bary s viacerými variantmi (výstup nad high predošlej sviečky / %R / oboje, stop, veľkosť z rizika so stropom
straty) a štyri profily, ktoré prešli smernicou, na MNQ (keď sú sviečky v sklade). Bez C# kompilátora sa preskočí.
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
from tradebot.strategies.wprnet import CONFIG_DIR  # noqa: E402

VARIANTS = {
    "default": {},
    "vystup_wpr": {"exitMode": 1, "exitLevel": -10.0, "stopPct": 0.25},
    "vystup_high": {"exitMode": 0, "entryLevel": -95.0, "wprLen": 9},
    "strop_straty_skipOverRisk": {"stopPct": 0.2, "fixedQty": False, "riskDollar": 100.0, "skipOverRisk": True},
    "riziko": {"stopPct": 0.5, "fixedQty": False, "riskDollar": 400.0},
}


def _walk(days: int, seed: int = 31) -> pd.DataFrame:
    """1m sviečky indexu (tick 0,25) od 20. 10. 2026."""
    rng = random.Random(seed)
    rows, price = [], 20000.0
    t0 = pd.Timestamp("2026-10-20 00:00", tz="UTC")
    for i in range(days * 1440):
        op = round((price + rng.choice((0.0, 0.0, rng.uniform(-3, 3)))) * 4) / 4
        close = round((op + rng.gauss(0, 4)) * 4) / 4
        high = max(op, close) + round(abs(rng.gauss(0, 2)) * 4) / 4
        low = min(op, close) - round(abs(rng.gauss(0, 2)) * 4) / 4
        rows.append((t0 + pd.Timedelta(minutes=i), op, high, low, close, round(rng.uniform(5, 400), 1)))
        price = close
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


@pytest.fixture(scope="module")
def frames():
    base = _walk(10)
    return {m: _with_ts(base if m == 1 else resample_ohlcv(base, m)) for m in (1, 5, 15, 60)}


def _plain(path: Path, tmp_path: Path) -> Path:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_strategy", None)          # ten istý profil pre predlohu aj C# port
    out = tmp_path / path.name
    out.write_text(json.dumps(data), encoding="utf-8")
    return out


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_wpr_synteticke_bary(frames, name, tmp_path):
    prof = tmp_path / "p.json"
    prof.write_text(json.dumps({"_instrument": "mnq_databento"}), encoding="utf-8")
    res = csharp_parity.compare_frames("wpr", "wprnet", str(prof), frames[5], lambda tf: frames[int(tf.rstrip("m"))], 5,
                                       None, None, VARIANTS[name], 10)
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 0, res["counts"]


@pytest.mark.parametrize("path", sorted(CONFIG_DIR.glob("PRESIEL_SMERNICAMI_*.json")), ids=lambda p: p.stem)
def test_wpr_presle_profily_mnq(path, tmp_path):
    tf = int(json.loads(path.read_text())["_timeframe"].rstrip("m"))
    try:
        res = csharp_parity.compare("wpr", "wprnet", str(_plain(path, tmp_path)), "mnq", tf, "2026-03-01", "2026-04-15")
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
