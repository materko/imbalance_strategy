"""MTK EMAS 1.0 (C# jadro, `mtkemasnet` a kópie trhov) proti Python predlohe (`mtkemas`) — bar po bare, na rovnosť.

Syntetické bary bežia vždy (všetkých 9 typov priemerov, price aj cross, trailing od R, zámok, cieľ, oba smery,
bez opačného výstupu, obaly vstupov); profily trhov zo štúdie na skutočných dátach len keď sú v sklade sviečky.
Bez C# kompilátora (csc / Mono) sa preskočí.
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

PROFILE = "mnq_databento_4h"

VARIANTS = {
    "hma_cena_trailing_zamok": {"maType": "hma", "signalMode": "price", "slowLen": 30, "trailAtr": 4.0, "beAtR": 1.0},
    "ema_cross_oba_smery_ciel": {"maType": "ema", "signalMode": "cross", "fastLen": 5, "slowLen": 13,
                                 "tradeDirection": "Both", "rrTarget": 2.0, "trendFilter": "off"},
    "sma_cena_bez_filtra": {"maType": "sma", "signalMode": "price", "slowLen": 20, "trendFilter": "off"},
    "wma_bez_opacneho_vystupu": {"maType": "wma", "signalMode": "price", "slowLen": 15, "exitOnSignal": False,
                                 "trendFilter": "off"},
    "dema_cross": {"maType": "dema", "signalMode": "cross", "fastLen": 5, "slowLen": 20, "trendFilter": "off"},
    "tema_cena": {"maType": "tema", "signalMode": "price", "slowLen": 10, "trendFilter": "off"},
    "rma_cena_zamok_bez_trailingu": {"maType": "rma", "signalMode": "price", "slowLen": 20, "trailAtr": 0.0,
                                     "beAtR": 1.0, "trendFilter": "off"},
    "vwma_cross": {"maType": "vwma", "signalMode": "cross", "fastLen": 3, "slowLen": 20, "trendFilter": "off"},
    "kama_cross_trailing_od_r": {"maType": "kama", "signalMode": "cross", "fastLen": 3, "slowLen": 8, "trailFromR": 1.0,
                                 "slAtr": 3.0, "trailAtr": 3.0, "trendFilter": "off"},
    "short_len_spicka": {"maType": "ema", "signalMode": "price", "slowLen": 20, "tradeDirection": "Short only",
                         "trendFilter": "off", "spikeFilter": True, "spikeShortDays": 2, "spikeLongDays": 5, "spikeMax": 1.1},
}


@pytest.fixture(scope="module")
def frames():
    from tradebot.core.candles import resample_ohlcv

    base = _random_walk(120 * 1440)
    return {m: _with_ts(base if m == 1 else resample_ohlcv(base, m)) for m in (1, 60)}


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_synteticke_bary(frames, name):
    res = csharp_parity.compare_frames(
        "mtkemas", "mtkemasnet", PROFILE, frames[60], lambda tf: frames[int(tf.rstrip("m"))] if tf.endswith("m") else frames[60], 60,
        None, None, VARIANTS[name], 10,
    )
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] >= 3, res["counts"]


#: kľúč trhu pre sklad sviečok → (predloha, C# kľúč)
MARKETS = {"mnq": ("mtkemas", "mtkemasnet"), "mgc": ("mtkemasmgc", "mtkemasmgcnet"), "es": ("mtkemases", "mtkemasesnet"),
           "mym": ("mtkemasmym", "mtkemasmymnet"), "btc": ("mtkemasbtc", "mtkemasbtcnet")}
_TF = {"30m": 30, "1h": 60, "2h": 120, "4h": 240, "1d": 1440}


def _profiles():
    from tradebot.strategies import STRATEGIES

    out = []
    for market, (base, net) in MARKETS.items():
        for p in sorted(Path(STRATEGIES[net].profile_dir).glob("*.json")):
            out.append(pytest.param(market, base, net, p, id=f"{net}-{p.stem}"))
    return out


@pytest.mark.parametrize("market,base,net,path", _profiles())
def test_profily_studie_na_trhu(market, base, net, path, tmp_path):
    """Každý profil zo štúdie dá v C# na svojom trhu (2021-10 – 2026-09) presne to isté ako Python kópia."""
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_strategy", None)
    tf = _TF[data["_timeframe"]]
    profile = tmp_path / "p.json"
    profile.write_text(json.dumps(data), encoding="utf-8")
    try:
        res = csharp_parity.compare(base, net, str(profile), market, tf, "2021-10-01", "2026-09-04")
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 10, res["counts"]
