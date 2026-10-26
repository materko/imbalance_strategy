"""ES stratégie s C# jadrom proti Python predlohe — bar po bare, na rovnosť.

* `nyvaesnet` (NY VA BREAKOUT ES, C#) proti `nyvaes` (Python) — varianty na syntetických baroch cez zmenu času
  v Európe (25. 10.) aj v USA (1. 11.) a všetkých päť profilov, ktoré prešli smernicou, na ES (keď sú sviečky v sklade),
* `ibsentryesnet` (IBS EZ ES, C#) proti `ibsentryes` (Python) — profil, ktorý prešiel smernicou, na ES.

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
from tradebot.strategies.ibsentryesnet import CONFIG_DIR as IBS_DIR  # noqa: E402
from tradebot.strategies.nyvaesnet import CONFIG_DIR as NYVA_DIR  # noqa: E402

PROFILE_1 = NYVA_DIR / "PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_1.json"

VARIANTS = {
    "profil_1": {},
    "close_tvar_vwap": {"entryMode": "close", "useShape": True, "shapePocPct": 52.0, "shapeVaPct": 50.0, "shapeTailPct": 40.0,
                        "useVwap": True, "confirmCloses": 2, "vaMinPoints": 0.0, "trendFilter": "off", "entryConfirm": "none"},
    "zavretie_v_case_strop_skip": {"entryMode": "close", "useCloseTime": True, "closeH": 11, "closeM": 0, "maxSlPoints": 15.0,
                                   "slCapMode": "skip", "maxSlAtr": 0.0, "vaMinPoints": 0.0, "maxTradesPerDay": 3,
                                   "fixedQty": True, "qty": 2.0, "trendFilter": "off", "entryConfirm": "none"},
    "strop_straty_skipOverRisk": {"entryMode": "close", "skipOverRisk": True, "riskDollar": 300.0, "vaMinPoints": 0.0,
                                  "maxSlAtr": 0.0, "trendFilter": "off", "entryConfirm": "none", "maxTradesPerDay": 3},
    "retest_len_short_iny_range": {"rangeStartH": 9, "rangeStartM": 45, "rangeEndH": 11, "rangeEndM": 0, "allowLong": False,
                                   "retestBars": 3, "profileRows": 25, "valueAreaPct": 60.0, "vaMinPoints": 0.0,
                                   "vaMaxPoints": 400.0, "entryConfirm": "none", "trendFilter": "off"},
}


def _walk(days: int, seed: int = 11) -> pd.DataFrame:
    """1m sviečky od 20. 10. 2026 — cez zmenu času v Európe (25. 10.) aj v USA (1. 11.), tick 0,25."""
    rng = random.Random(seed)
    rows, price = [], 6500.0
    t0 = pd.Timestamp("2026-10-20 00:00", tz="UTC")
    for i in range(days * 1440):
        op = round((price + rng.choice((0.0, 0.0, 0.0, rng.uniform(-3, 3)))) * 4) / 4
        close = round((op + rng.gauss(0, 1.6)) * 4) / 4
        high = max(op, close) + round(abs(rng.gauss(0, 0.8)) * 4) / 4
        low = min(op, close) - round(abs(rng.gauss(0, 0.8)) * 4) / 4
        rows.append((t0 + pd.Timedelta(minutes=i), op, high, low, close, round(rng.uniform(10, 900), 1)))
        price = close
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


@pytest.fixture(scope="module")
def frames():
    base = _walk(16)
    return {m: _with_ts(base if m == 1 else resample_ohlcv(base, m)) for m in (1, 3, 5, 15, 60)}


def _plain(path: Path, tmp_path: Path) -> Path:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_strategy", None)          # ten istý profil pre predlohu aj C# port
    out = tmp_path / path.name
    out.write_text(json.dumps(data), encoding="utf-8")
    return out


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_nyva_synteticke_bary_cez_zmenu_casu(frames, name, tmp_path):
    res = csharp_parity.compare_frames(
        "nyvaes", "nyvaesnet", str(_plain(PROFILE_1, tmp_path)), frames[3], lambda tf: frames[int(tf.rstrip("m"))], 3,
        None, None, VARIANTS[name], 10,
    )
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["drawings"] > 20, res["counts"]


@pytest.mark.parametrize("path", sorted(NYVA_DIR.glob("PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_*.json")), ids=lambda p: p.stem)
def test_nyva_presle_profily_na_es(path, tmp_path):
    try:
        res = csharp_parity.compare("nyvaes", "nyvaesnet", str(_plain(path, tmp_path)), "es", 3, "2025-09-04", "2026-09-04")
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]


@pytest.mark.parametrize("path", sorted(IBS_DIR.glob("PRESIEL_SMERNICAMI_IBS_EZ_ES_*.json")), ids=lambda p: p.stem)
def test_ibs_ez_es_presly_profil_na_es(path, tmp_path):
    try:
        res = csharp_parity.compare("ibsentryes", "ibsentryesnet", str(_plain(path, tmp_path)), "es", 3,
                                    "2026-03-01", "2026-06-01")
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
