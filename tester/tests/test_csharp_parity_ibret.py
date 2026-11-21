"""IB RETRACE 1.0 (C# jadro, `ibretnet`) proti IB RETRACE 1.0 (Python, `ibret`) — bar po bare, na rovnosť.

C# jadro je prepis, nie nová stratégia: na rovnakých vstupoch musí dať rovnaké ordery a kresby do posledného bitu.
Syntetické bary bežia vždy (všetky vetvy: limitka / market, cieľ extenzia / RR, zrušenie limitky, okno prierazu,
dni v týždni, šírka IB, koniec dňa, obaly vstupov); posledný rok MNQ len keď sú v sklade sviečky.
Bez C# kompilátora (csc / Mono) sa preskočí.
"""

from __future__ import annotations

import json

import pytest

from tradebot.adapters.csharp import build as csbuild

try:
    csbuild.ensure_built()
except csbuild.BuildError as exc:  # pragma: no cover - stroj bez C# kompilátora
    pytest.skip(f"C# jadro sa nedá preložiť: {exc}", allow_module_level=True)

from tester.compare import csharp_parity  # noqa: E402
from tester.tests.test_csharp_parity import _random_walk, _with_ts  # noqa: E402
from tradebot.core.entry_confirm import EntryConfirm  # noqa: E402
from tradebot.core.entry_filter import TrendFilter  # noqa: E402
from tradebot.core.entry_order import EntryOrderType  # noqa: E402

PROFILE = "mnq_databento_5m"

VARIANTS = {
    "zdroj": {},
    "zatvorenie": {"breakOn": "close"},
    "short_vlastne_urovne": {"shortLevels": True, "shortEntryRetr": 0.1, "shortSlRetr": 0.7, "shortTpExt": 0.8,
                             "shortRr": 2.0, "slRetr": 0.6},
    "short_vlastne_rr": {"shortLevels": True, "tpMode": "rr", "rr": 2.0, "shortRr": 1.25, "shortSlRetr": 0.9,
                         "breakOn": "close"},
    "telo_bias_with_ib_pct": {"breakOn": "body", "biasFilter": "with", "minIbPct": 0.2, "maxIbPct": 3.0},
    "bez_konca_dna": {"closeAtEnd": False, "tpMode": "rr", "rr": 2.0, "slRetr": 1.1},
    "bias_against_ib_rel": {"biasFilter": "against", "ibAvgDays": 5, "minIbRel": 0.6, "maxIbRel": 1.6},
    "breakout_rr": {"entryMode": "breakout", "tpMode": "rr", "rr": 1.0, "minRR": 0.5},
    "short_rezerva_dni": {"tradeDirection": "Short only", "slBufferTicks": 8, "tradeMon": False, "tradeFri": False},
    "okno_sirka_bez_konca": {"breakFrom": 1035, "breakTo": 1300, "lastEntry": 1500, "closeAtEnd": False,
                             "maxIbPoints": 400.0, "entryRetr": 0.0, "slRetr": 0.6},
    "ib_30_long_pevny": {"ibMinutes": 30, "breakFrom": 1000, "tradeDirection": "Long only", "fixedQty": True, "qty": 2.0,
                         "exitTime": 1500},
    "obaly_filter_potvrdenie_limitka": {"entryMode": "breakout", "minRR": 0.0, "trendFilter": TrendFilter.WITH,
                                        "trendTF": 15, "trendEmaLen": 10, "entryConfirm": EntryConfirm.ANY,
                                        "confirmBars": 6, "entryOrderType": EntryOrderType.LIMIT, "limitOffsetPct": 30},
}


@pytest.fixture(scope="module")
def frames():
    from tradebot.core.candles import resample_ohlcv

    base = _random_walk(60 * 1440)
    return {m: _with_ts(base if m == 1 else resample_ohlcv(base, m)) for m in (1, 5, 15)}


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_synteticke_bary(frames, name):
    res = csharp_parity.compare_frames(
        "ibret", "ibretnet", PROFILE, frames[5], lambda tf: frames[int(tf.rstrip("m"))], 5,
        None, None, VARIANTS[name], 10,
    )
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] >= 3, res["counts"]


@pytest.mark.parametrize("name", ["zdroj", "breakout_rr"])
def test_mnq_posledny_rok(name, tmp_path):
    profile = tmp_path / "p.json"
    profile.write_text(json.dumps({"_instrument": "mnq_databento", "_timeframe": "5m", **VARIANTS[name]}), encoding="utf-8")
    try:
        res = csharp_parity.compare("ibret", "ibretnet", str(profile), "mnq", 5, "2025-09-04", "2026-09-04")
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 10, res["counts"]


#: IB RETRACE na MGC a MYM (21. 11. 2026): vlastné kľúče C# nad tým istým `IbRetEngine`; kód trhu pre sklad sviečok.
MARKETS = {"mgc": ("ibretmgc", "ibretmgcnet"), "mym": ("ibretmym", "ibretmymnet")}


@pytest.mark.parametrize("market", sorted(MARKETS))
def test_trhy_posledny_rok(market, tmp_path):
    """Východiskový profil trhu dá v C# na svojom trhu presne to isté ako Python kópia (aj s filtrami IB)."""
    from pathlib import Path

    from tradebot.strategies import STRATEGIES

    base, net = MARKETS[market]
    spec = STRATEGIES[net]
    data = json.loads((Path(spec.profile_dir) / f"{spec.default_profile}.json").read_text(encoding="utf-8"))
    data.pop("_strategy", None)     # ten istý profil pre predlohu aj C# port
    data.update({"biasFilter": "with", "minIbRel": 0.5, "maxIbRel": 2.0, "closeAtEnd": False})
    profile = tmp_path / "p.json"
    profile.write_text(json.dumps(data), encoding="utf-8")
    try:
        res = csharp_parity.compare(base, net, str(profile), market, 5, "2025-09-04", "2026-09-04")
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    assert res["mismatches"] == [], res["mismatches"][:3]
    assert res["counts"]["entries"] > 20, res["counts"]
