"""SPRÁVY s C# jadrom (`spravynet`) proti Python predlohe `spravy` — bar po bare, na rovnosť.

Syntetické 1m sviečky od 20. 10. 2026 cez zmenu času na Slovensku (25. 10.) aj v USA (1. 11.): FOMC 28. 10. je o 19:00 SK,
4. 11. zase o 20:00 SK — engine to musí trafiť v oboch jazykoch rovnako. Potom skutočné MGC, keď sú sviečky v sklade.
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
from tradebot.strategies.spravy import CONFIG_DIR  # noqa: E402
from tradebot.strategies.spravy.calendar import csharp_source  # noqa: E402

PROFILE = CONFIG_DIR / "mgc_databento_5m.json"
RISK = CONFIG_DIR / "mgc_databento_5m_riziko500.json"

VARIANTS = {
    "profil": {},
    "tlacovka_zapnuta": {"r2Event": "FOMC", "r1Hold": 25},
    "vsetky_spravy": {**{f"use{t}": True for t in ("NFP", "GDP", "ISM_M", "ISM_S", "RETAIL", "FOMC_MIN", "CLAIMS")},
                      "r2Event": "NFP", "r7Event": "GDP", "r7Mode": "fade", "r8Event": "CLAIMS", "r8From": -30, "r8To": 0, "r8Enter": 5},
    "stop_za_nohou_ciel_2R": {"r3Stop": 0.0, "r5Stop": 1.0, "r1RR": 0.0, "r3RR": 1.0, "minLeg": {"value": 0.5, "unit": "atr"}},
    "bez_cielov": {f"r{n}RR": 0.0 for n in range(1, 9)},
    "riziko_s_minimom": {"fixedQty": False, "riskDollar": 300.0, "sizeMinRisk": 5.0},
    "strop_straty_skipOverRisk": {"skipOverRisk": True, "riskDollar": 150.0, "fixedQty": True, "qty": 2.0},
    "opravy_kalendara": {"newsAdd": "2026-10-27 10:00 JOLTS; 2026-10-30 08:30 PCE", "newsSkip": "2026-10-28 FOMC"},
    "len_short_kratke_drzanie": {"allowLong": False, "r1Hold": 20, "r5Hold": 45, "r5From": 5, "r5To": 30, "r5Enter": 35},
    "prepinace_vypnute": {"useFOMC": False, "useCPI": False},
    "pred_spravou_viac_pravidiel": {"r2Event": "FOMC", "r2Mode": "fade", "r2From": -30, "r2To": -5, "r2Enter": 0, "r2Hold": 15,
                                    "r1Event": "FOMC", "r1From": -60, "r1To": 0, "r1Enter": 20, "r1Hold": 30},
}


def _walk(days: int, seed: int = 11) -> pd.DataFrame:
    """1m sviečky zlata od 20. 10. 2026 — cez zmenu času na Slovensku (25. 10.) aj v USA (1. 11.), tick 0,1."""
    rng = random.Random(seed)
    rows, price = [], 4000.0
    t0 = pd.Timestamp("2026-10-20 00:00", tz="UTC")
    tick = 0.1
    for i in range(days * 1440):
        op = round((price + rng.choice((0.0, 0.0, rng.uniform(-1.5, 1.5)))) / tick) * tick
        close = round((op + rng.gauss(0, 0.9)) / tick) * tick
        high = max(op, close) + round(abs(rng.gauss(0, 0.5)) / tick) * tick
        low = min(op, close) - round(abs(rng.gauss(0, 0.5)) / tick) * tick
        rows.append((t0 + pd.Timedelta(minutes=i), op, high, low, close, round(rng.uniform(10, 900), 1)))
        price = close
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


@pytest.fixture(scope="module")
def frames():
    base = _walk(20)
    return {m: _with_ts(base if m == 1 else resample_ohlcv(base, m)) for m in (1, 3, 5, 15)}


def _plain(path: Path, tmp_path: Path) -> Path:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_strategy", None)          # ten istý profil pre predlohu aj C# port
    out = tmp_path / path.name
    out.write_text(json.dumps(data), encoding="utf-8")
    return out


def test_csharp_kalendar_je_vygenerovany_z_json():
    cs = (Path(__file__).resolve().parents[2] / "tradebot" / "strategies" / "spravy" / "ports" / "csharp"
          / "SpravyCalendar.cs").read_text(encoding="utf-8")
    assert cs == csharp_source(), "SpravyCalendar.cs nesedí s calendar.json — python -m tradebot.strategies.spravy.calendar --cs"


@pytest.mark.parametrize("name", sorted(VARIANTS))
@pytest.mark.parametrize("tf", [5, 3])
def test_synteticke_bary_cez_zmenu_casu(frames, name, tf, tmp_path):
    res = csharp_parity.compare_frames(
        "spravy", "spravynet", str(_plain(PROFILE, tmp_path)), frames[tf], lambda t: frames[int(t.rstrip("m"))], tf,
        None, None, VARIANTS[name], 10,
    )
    assert res["mismatches"] == [], res["mismatches"][:3]


@pytest.mark.parametrize("profile", [PROFILE, RISK])
def test_na_mgc(profile, tmp_path):
    try:
        res = csharp_parity.compare("spravy", "spravynet", str(_plain(profile, tmp_path)), "mgc", 5, "2025-09-01", "2026-06-01")
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["drawings"] > 50, res["counts"]
