"""VWAP ADX Pullback (C# jadro, `vwapadxnet`) proti VWAP ADX Pullback (Python, `vwapadx`) — bar po bare, na rovnosť.

C# jadro je prepis, nie nová stratégia: na rovnakých vstupoch musí dať rovnaké ordery a kresby do posledného
bitu. Syntetické bary bežia vždy; prešlé profily zo smernice (`tester/profiles/PRESIEL_SMERNICAMI_VWAP_ADX_Pullback_*`)
na MNQ len keď sú v sklade sviečky. Bez C# kompilátora (csc / Mono) sa preskočí.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradebot.adapters.csharp import build as csbuild

try:
    csbuild.ensure_built()
except csbuild.BuildError as exc:  # pragma: no cover - stroj bez C# kompilátora
    pytest.skip(f"C# jadro sa nedá preložiť: {exc}", allow_module_level=True)

from tester.compare import csharp_parity  # noqa: E402
from tester.tests.test_csharp_parity import _random_walk, _with_ts  # noqa: E402
from tradebot.core.entry_confirm import EntryConfirm  # noqa: E402
from tradebot.core.entry_filter import TrendFilter, VolFilter  # noqa: E402
from tradebot.core.entry_order import EntryOrderType  # noqa: E402
from tradebot.core.paths import PROFILES_DIR  # noqa: E402
from tradebot.strategies.vwapadx.config import VwapAnchor  # noqa: E402

PROFILE = "mnq_databento_1m"

#: Na náhodnej prechádzke má ADX aj pullback k VWAP prísť často: nízky prah, viac obchodov denne.
LOOSE = {"adxMin": 5.0, "maxTrades": 5}

VARIANTS = {
    "rth_casovy_exit": {"vwapAnchor": VwapAnchor.RTH, "useTimeExit": True},
    "polnoc_bez_exitu_pine_sizing": {"vwapAnchor": VwapAnchor.MIDNIGHT, "useTimeExit": False, "legacyPineSizing": True,
                                     "tpBars": 12, "slBars": 6},
    "obaly_filter_potvrdenie_limitka": {"trendFilter": TrendFilter.WITH, "trendTF": 15, "trendEmaLen": 10,
                                        "volFilter": VolFilter.HIGH, "volLookback": 30,
                                        "entryConfirm": EntryConfirm.ANY, "confirmBars": 6,
                                        "entryOrderType": EntryOrderType.LIMIT, "limitOffsetPct": 30},
}


@pytest.fixture(scope="module")
def frames():
    base = _random_walk(10 * 1440)
    return {m: _with_ts(base if m == 1 else _resample(base, m)) for m in (1, 3)}


def _resample(df, minutes):
    from tradebot.core.candles import resample_ohlcv

    return resample_ohlcv(df, minutes)


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_synteticke_bary(frames, name):
    res = csharp_parity.compare_frames(
        "vwapadx", "vwapadxnet", PROFILE, frames[1], lambda tf: frames[int(tf.rstrip("m"))], 1,
        "2026-03-28", None, {**LOOSE, **VARIANTS[name]}, 10,
    )
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["drawings"] > 20, res["counts"]


def _passed_profiles() -> list[Path]:
    return sorted(PROFILES_DIR.glob("PRESIEL_SMERNICAMI_VWAP_ADX_Pullback_[0-9]*.json"),
                  key=lambda p: int(p.stem.rsplit("_", 1)[1]))


@pytest.mark.parametrize("path", _passed_profiles(), ids=lambda p: p.stem)
def test_presle_profily_smernice_na_mnq(path, tmp_path):
    """Nastavenia, ktoré prešli smernicou, musia v C# dať na MNQ (posledný rok) presne to isté."""
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_strategy", None)     # ten istý profil pre predlohu aj C# port
    profile = tmp_path / path.name
    profile.write_text(json.dumps(data), encoding="utf-8")
    tf = int(str(data.get("_timeframe", "3m")).rstrip("m"))
    try:
        res = csharp_parity.compare("vwapadx", "vwapadxnet", str(profile), "mnq", tf, "2025-09-04", "2026-09-04")
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 50, res["counts"]
