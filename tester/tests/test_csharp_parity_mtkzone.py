"""MTK ZONE (C# jadro, `mtkzonenet`) proti MTK ZONE (Python, `mtkzone`) — bar po bare, na rovnosť.

C# jadro je prepis, nie nová stratégia: na rovnakých vstupoch musí dať rovnaké ordery a kresby do posledného bitu.
Syntetické bary bežia vždy (všetky zdroje zón, všetky tri vstupné modely, VWAP a seansa); profil na MNQ len keď
sú v sklade sviečky. Bez C# kompilátora (csc / Mono) sa preskočí.
"""

from __future__ import annotations

import pytest

from tradebot.adapters.csharp import build as csbuild

try:
    csbuild.ensure_built()
except csbuild.BuildError as exc:  # pragma: no cover - stroj bez C# kompilátora
    pytest.skip(f"C# jadro sa nedá preložiť: {exc}", allow_module_level=True)

from tester.compare import csharp_parity  # noqa: E402
from tester.tests.test_csharp_parity import _random_walk, _with_ts  # noqa: E402
from tradebot.core.types import SizeSpec  # noqa: E402
from tradebot.strategies.mtkzone.config import TradeDirection, VwapAnchor, VwapMode  # noqa: E402

_S = SizeSpec(0.5, "abs")

PROFILE = "mnq_databento_3m"

#: Na náhodnej prechádzke treba zóny často: mäkšie prahy, viac zón.
LOOSE = {"minConf": 1, "minScore": 0.0, "volSpike": 1.3, "impMult": 0.8, "maxZones": 5, "usePocZone": True,
         "pocEvery": 7}

VARIANTS = {
    "limit_na_zonu": {"useLimit": True},
    "ibs_a_pin_bar": {"useLimit": False, "useIBS": True, "usePin": True, "st1Max": 3, "minImbSize": _S,
                      "imbMaxDistTicks": 400, "pbRatio": 1.5, "pbMinRange": _S},
    "dva_tf_vwap_seansa_riziko": {"useZ2": True, "zoneTf2": 15, "useIBS": True, "usePin": True, "vwapMode": VwapMode.AGAINST,
                                  "vwapAnchor": VwapAnchor.NY, "useSess": True, "sessStart": 300, "sessEnd": 2100,
                                  "fixedQty": False, "riskDollar": 200.0, "minGap": 3, "maxZoneAge": 400,
                                  "minImbSize": _S, "imbMaxDistTicks": 400, "pbRatio": 1.5, "pbMinRange": _S},
    "tyzden_with_maxdist": {"vwapMode": VwapMode.WITH, "vwapAnchor": VwapAnchor.WEEK, "maxDist": 40.0, "maxRiskTicks": 300,
                            "tradeDirection": TradeDirection.LONG_ONLY, "minConf": 2, "minScore": 20.0},
}


@pytest.fixture(scope="module")
def frames():
    base = _random_walk(12 * 1440)
    return {m: _with_ts(base if m == 1 else _resample(base, m)) for m in (1, 3)}


def _resample(df, minutes):
    from tradebot.core.candles import resample_ohlcv

    return resample_ohlcv(df, minutes)


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_synteticke_bary(frames, name):
    res = csharp_parity.compare_frames(
        "mtkzone", "mtkzonenet", PROFILE, frames[3], lambda tf: frames[int(tf.rstrip("m"))], 3,
        "2026-03-28", None, {**LOOSE, **VARIANTS[name]}, 10,
    )
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["drawings"] > 20, res["counts"]
