"""ORBNinja (C# jadro) proti ORB (Python) — bar po bare, na rovnosť.

To isté ako `test_csharp_parity.py` pre IBSNinja: C# jadro je prepis, nie nová stratégia, takže
na rovnakých vstupoch musí dať rovnaké ordery a kresby do posledného bitu. Syntetické bary bežia
vždy, okno NAS100 len keď sú v sklade sviečky. Bez C# kompilátora (csc / Mono) sa preskočí.
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
from tradebot.strategies.orb.config import (  # noqa: E402
    EntryMode, SessionMode, SlMode, TpMode, TradeDirection,
)

PROFILE = "nas100_dukascopy_3m"

#: Na náhodnej prechádzke s cenou 50 000 by Pine prahy šírky rangu nepustili nič — preto voľné
#: filtre, obe seansy, viac obchodov denne a víkendy, nech sa naozaj vstupuje.
LOOSE = {
    "sessionMode": SessionMode.BOTH, "weekdaysOnly": False, "minRangePct": 0.0, "maxRangePct": 10.0,
    "maxTradesPerDay": 4, "entryWindowMinutes": 0, "minClosePosPct": 0,
}

VARIANTS = {
    "close_opposite_rr": {"entryMode": EntryMode.CLOSE, "slMode": SlMode.OPPOSITE, "tpMode": TpMode.RR},
    "retest_range_pct_measured": {"entryMode": EntryMode.RETEST, "slMode": SlMode.RANGE_PCT,
                                  "tpMode": TpMode.MEASURED, "retestMaxBars": 4},
    "stop_break_candle_atr": {"entryMode": EntryMode.STOP, "slMode": SlMode.BREAK_CANDLE, "tpMode": TpMode.ATR},
    "mid_trailing_volume": {"slMode": SlMode.MID, "enableTrailing": True, "useVolumeFilter": True,
                            "volMultiplier": 1.0, "nyRangeMinutes": 30, "lonRangeMinutes": 7},
    "atr_long_only_legacy": {"slMode": SlMode.ATR, "tradeDirection": TradeDirection.LONG_ONLY,
                             "legacyPineSizing": True, "closeAtSessionEnd": False,
                             "minSlDistance": SizeSpec(0.02, "pct")},
    "ema_filter_exit_kreslenie": {"emaLen": 30, "emaFilter": True, "emaExit": True, "showEma": True},
    "ema_filter_dna": {"emaLen": 50, "emaRangeFilter": True, "entryMode": EntryMode.RETEST, "retestMaxBars": 6},
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
        "orb", "orbninja", PROFILE, frames[3], lambda tf: frames[int(tf.rstrip("m"))], 3,
        "2026-03-28", None, {**LOOSE, **VARIANTS[name]}, 10,
    )
    assert res["mismatches"] == [], res["mismatches"][:3]
    # bez vstupov by zhoda nič neznamenala
    assert res["counts"]["entries"] > 5 and res["counts"]["drawings"] > 20, res["counts"]


def test_stdio_transport_dava_to_iste(frames, monkeypatch):
    """Samostatný proces (`TradeBot.Host.exe`) musí dať to isté čo pythonnet."""
    monkeypatch.setenv("TRADEBOT_CSHARP_BRIDGE", "stdio")
    res = csharp_parity.compare_frames(
        "orb", "orbninja", PROFILE, frames[3], lambda tf: frames[int(tf.rstrip("m"))], 3,
        "2026-03-28", None, {**LOOSE, **VARIANTS["mid_trailing_volume"]}, 10,
    )
    assert res["mismatches"] == [], res["mismatches"][:3]


def test_okno_nas100():
    try:
        res = csharp_parity.compare("orb", "orbninja", PROFILE, "nas100", 3, "2025-09-04", "2026-09-04")
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 100
