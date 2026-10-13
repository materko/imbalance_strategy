"""VWAP ORB (C# jadro, `vwaporbnet`) proti VWAP ORB (Python, `vwaporb`) — bar po bare, na rovnosť.

C# jadro je prepis, nie nová stratégia: na rovnakých vstupoch musí dať rovnaké ordery a kresby do posledného
bitu. Syntetické bary bežia vždy; prešlé profily zo smernice (`tester/profiles/PRESIEL_SMERNICAMI_VWAP_ORB_*`)
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
from tradebot.core.config import ConfigError  # noqa: E402
from tradebot.core.entry_filter import TrendFilter, VolFilter  # noqa: E402
from tradebot.core.paths import PROFILES_DIR  # noqa: E402
from tradebot.core.types import SizeSpec  # noqa: E402
from tradebot.strategies.orb.config import SlMode  # noqa: E402
from tradebot.strategies.vwapdrift.config import VwapAnchor, VwapPeriod  # noqa: E402
from tradebot.strategies.vwaporb.config import EntryTiming, ExitMode, VwapRule  # noqa: E402

PROFILE = "mnq_databento_5m"

#: Na náhodnej prechádzke sa má naozaj vstupovať: voľné filtre, viac obchodov denne, aj víkendy.
LOOSE = {"weekdaysOnly": False, "maxTradesPerDay": 4, "minRangePct": 0.0, "maxRangePct": 10.0}

VARIANTS = {
    "break_15m_tp": {"vwapRule": VwapRule.BREAK, "vwapPeriod": VwapPeriod.M15},
    "direction_chart_vwap_exit": {"vwapRule": VwapRule.DIRECTION, "vwapPeriod": VwapPeriod.CHART,
                                  "exitMode": ExitMode.VWAP, "closeBeyondVwap": True},
    "break_candle_tp_vwap": {"vwapRule": VwapRule.DIRECTION, "entryTiming": EntryTiming.BREAK_CANDLE,
                             "exitMode": ExitMode.TP_VWAP, "vwapExitAtr": SizeSpec(0.2, "atr"),
                             "vwapDriftMinAtr": SizeSpec(0.02, "atr")},
    "session_kotva_mid": {"vwapAnchor": VwapAnchor.SESSION, "vwapRule": VwapRule.DIRECTION,
                          "vwapPeriod": VwapPeriod.CHART, "slMode": SlMode.MID},
    "utc_den_break_atr": {"vwapAnchor": VwapAnchor.UTC_DAY, "vwapBreakAtr": SizeSpec(0.1, "atr")},
    "filter_trendu_a_volatility": {"vwapRule": VwapRule.DIRECTION, "vwapPeriod": VwapPeriod.CHART,
                                   "trendFilter": TrendFilter.WITH, "trendTF": 30, "trendEmaLen": 20,
                                   "volFilter": VolFilter.HIGH, "volLookback": 30},
}


@pytest.fixture(scope="module")
def frames():
    base = _random_walk(10 * 1440)
    return {m: _with_ts(base if m == 1 else _resample(base, m)) for m in (1, 3, 5)}


def _resample(df, minutes):
    from tradebot.core.candles import resample_ohlcv

    return resample_ohlcv(df, minutes)


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_synteticke_bary(frames, name):
    res = csharp_parity.compare_frames(
        "vwaporb", "vwaporbnet", PROFILE, frames[3], lambda tf: frames[int(tf.rstrip("m"))], 3,
        "2026-03-28", None, {**LOOSE, **VARIANTS[name]}, 10,
    )
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 3 and res["counts"]["drawings"] > 20, res["counts"]


def test_stop_s_vwap_csharp_port_odmietne():
    """`vwapStop` / `vwapTp` C# jadro nemá — config to povie skôr, než by beh ticho počítal niečo iné."""
    from tradebot.strategies.vwaporbnet.config import VwapOrbNetConfig

    for field in ("vwapStop", "vwapTp"):
        with pytest.raises(ConfigError, match="vwapStop / vwapTp"):
            VwapOrbNetConfig(**{field: True}).validate()


def _passed_profiles() -> list[Path]:
    return sorted(PROFILES_DIR.glob("PRESIEL_SMERNICAMI_VWAP_ORB_[0-9]*.json"),
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
        res = csharp_parity.compare("vwaporb", "vwaporbnet", str(profile), "mnq", tf, "2025-09-04", "2026-09-04")
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 50, res["counts"]
