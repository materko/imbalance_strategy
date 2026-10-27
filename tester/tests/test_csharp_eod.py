"""EOD kópie C# stratégií (`<kľúč>eod`) proti predlohe — o 15:59 New York je všetko zavreté, inak to isté.

`EodCloseEngine` (`tradebot/core/ports/csharp/TradeBot.Core/EodClose.cs`) obalí engine predlohy aj s jeho obalmi vstupov. Kontroluje sa:

* **až po prvý zásah EOD** sú ordery, kresby aj koniec seansy bar po bare tie isté ako pri predlohe (mimo okna sa
  nesmie zmeniť nič) — prvý rozdiel smie byť len na bare v okne EOD;
* **v okne EOD** (posledný bar, ktorý sa zatvára najneskôr o 15:59 NY, až do 18:00 NY) nevznikne žiadny vstup a po bare
  nie je otvorená pozícia ani čakajúci vstupný order — v tom istom modeli vyplnenia, ktorým beží porovnanie parity;
* predloha v tých istých dátach pozície cez 15:59 naozaj drží (inak by test nič neoveril).

Syntetické bary bežia vždy (aj s limitkou a potvrdením, aby sa rušili čakajúce ordery); profily `SMERNICE_CS_EOD_*_1`
na MNQ len keď sú v sklade sviečky. Bez C# kompilátora (csc / Mono) sa preskočí.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from tradebot.adapters.csharp import build as csbuild

try:
    csbuild.ensure_built()
except csbuild.BuildError as exc:  # pragma: no cover - stroj bez C# kompilátora
    pytest.skip(f"C# jadro sa nedá preložiť: {exc}", allow_module_level=True)

from tester.compare.csharp_parity import _capture, _plain  # noqa: E402
from tester.compare.scan_zones import _load, _to_bar  # noqa: E402
from tester.tests.test_csharp_parity import _random_walk, _with_ts  # noqa: E402
from tradebot.adapters.freqtrade.runner import EngineRunner  # noqa: E402
from tradebot.core import load_profile  # noqa: E402
from tradebot.core.entry_confirm import EntryConfirm  # noqa: E402
from tradebot.core.entry_order import EntryOrderType  # noqa: E402
from tradebot.core.orders import OrderAction  # noqa: E402
from tradebot.core.paths import PROFILES_DIR  # noqa: E402
from tradebot.core.types import SizeSpec  # noqa: E402
from tradebot.core.warmup import seed_engine  # noqa: E402
from tradebot.strategies import get_spec  # noqa: E402

NY = ZoneInfo("America/New_York")
CLOSE_MIN, REOPEN_MIN = 15 * 60 + 59, 18 * 60

#: predloha -> (profil, TF, voľnejšie nastavenie pre náhodnú prechádzku) — ako v testoch parity predlôh
BASES = {
    "ibsentrynet": ("golden_binance_btcusdt_3m", 3,
                    {"weekdaysOnly": False, "zoneValidHours": 4, "enableFvgTrading": True,
                     "fvgMinSize": SizeSpec(10.0, "abs"), "closeAtSessionEnd": False, "rrRatio": 6.0,
                     # obchodné okno cez 15:59 NY, ako v nastaveniach zo smernice (14:00–19:45 NY)
                     **{f"sess{n}{k}": v for n in (1, 2, 3) for k, v in (("On", n == 1), ("TZ", "America/New_York"))},
                     "sess1ZoneStartH": 0, "sess1ZoneStartM": 0, "sess1ZoneEndH": 23, "sess1ZoneEndM": 59,
                     "sess1TradeStartH": 14, "sess1TradeStartM": 0, "sess1TradeEndH": 19, "sess1TradeEndM": 45}),
    "vwaporbnet": ("mnq_databento_5m", 3, {"weekdaysOnly": False, "maxTradesPerDay": 4, "minRangePct": 0.0,
                                           "maxRangePct": 10.0}),
    "vwapadxnet": ("mnq_databento_1m", 3, {"adxMin": 5.0, "maxTrades": 5, "useTimeExit": False,
                                           "tpBars": 200, "slBars": 200}),
    "noanet": ("mnq_databento_5m", 5, {"lookbackDays": 5, "checkEvery": 15, "maxTradesPerDay": 10,
                                       "weekdaysOnly": False}),
    "tksnet": ("mnq_databento_3m", 3, {"lookbackDays": 5, "rrRatio": 3.0, "pivLen": 8, "loLevel": 45.0, "hiLevel": 55.0,
                                       "nConf": 1}),
}

#: obaly vstupov — vstupy, ktoré čakajú, a teda ordery, ktoré musí EOD zrušiť (dlhá limitka čaká aj cez 15:59)
WRAPS = {
    "market": {},
    "limitka_potvrdenie": {"entryConfirm": EntryConfirm.ANY, "confirmBars": 6,
                           "entryOrderType": EntryOrderType.LIMIT, "limitOffsetPct": 30},
    "limitka_dlha": {"entryOrderType": EntryOrderType.LIMIT, "limitOffsetPct": 60, "limitValidBars": 100},
}


def _in_window(ts_ms: int, tf: int) -> bool:
    t = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).astimezone(NY)
    m = t.hour * 60 + t.minute
    return m + 2 * tf > CLOSE_MIN and m < REOPEN_MIN


def _runner(key, profile, overrides, chart_all, htf_loader, tf, first_ms):
    cfg, inst = load_profile(profile, strategy=key)
    for name, value in (overrides or {}).items():
        setattr(cfg, name, value)
    cfg.validate()
    spec = get_spec(key)
    runner = EngineRunner(cfg, inst, tf, spec=spec)
    if runner.htf is not None:
        htf_df = htf_loader(spec.informative_tfs(cfg)[0]).copy()
        htf_df["vol_sma"] = htf_df["volume"].rolling(cfg.volSmaLen).mean()
        runner.htf.load(
            {int(r.ts): _to_bar(r) for r in htf_df.itertuples(index=False)},
            {int(r.ts): (float(r.vol_sma) if r.vol_sma == r.vol_sma else 0.0) for r in htf_df.itertuples(index=False)},
        )
    seed_engine(runner.engine, chart_all, first_ms)
    return runner, _capture(runner)


def _check(base_key, profile, overrides, chart_all, htf_loader, tf, date_from=None, date_to=None):
    import pandas as pd

    chart = chart_all
    if date_from:
        chart = chart[chart["date"] >= pd.Timestamp(date_from, tz="UTC")]
    if date_to:
        chart = chart[chart["date"] < pd.Timestamp(date_to, tz="UTC")]
    first_ms = int(chart["ts"].iloc[0])
    base, box_b = _runner(base_key, profile, overrides, chart_all, htf_loader, tf, first_ms)
    eod, box_e = _runner(base_key + "eod", profile, overrides, chart_all, htf_loader, tf, first_ms)

    same = True
    stats = {"bars": 0, "window_bars": 0, "base_held": 0, "eod_closes": 0, "eod_cancels": 0, "entries": 0}
    for row in chart.itertuples(index=False):
        bar = _to_bar(row)
        base.process(bar, base.htf.window_for(bar.time) if base.htf is not None else None)
        eod.process(bar, eod.htf.window_for(bar.time) if eod.htf is not None else None)
        ob, oe = box_b[0], box_e[0]
        win = _in_window(bar.time, tf)
        stats["bars"] += 1
        stats["entries"] += sum(o.action is OrderAction.ENTRY for o in oe.orders)
        if same:
            equal = (_plain(ob.orders) == _plain(oe.orders) and _plain(ob.drawings) == _plain(oe.drawings)
                     and ob.close_session == oe.close_session)
            if not equal:
                assert win, f"{base_key}: EOD sa líši od predlohy mimo okna EOD na bare {bar.time}"
                same = False
        if not win:
            continue
        stats["window_bars"] += 1
        stats["base_held"] += base._position != 0.0
        assert not [o for o in oe.orders if o.action is OrderAction.ENTRY], f"{base_key}eod: vstup v okne EOD {bar.time}"
        stats["eod_closes"] += sum(o.action is OrderAction.CLOSE and o.reason == "EOD 15:59 NY" for o in oe.orders)
        stats["eod_cancels"] += sum(o.action is OrderAction.CANCEL and o.reason == "EOD 15:59 NY" for o in oe.orders)
        assert eod._position == 0.0, f"{base_key}eod: pozícia po okne EOD {bar.time}"
        assert not [k for k, o in eod._orders.items() if not o.filled], f"{base_key}eod: čakajúci order po EOD {bar.time}"
    return stats


@pytest.fixture(scope="module")
def frames():
    from tradebot.core.candles import resample_ohlcv

    base = _random_walk(12 * 1440)
    return {m: _with_ts(base if m == 1 else resample_ohlcv(base, m)) for m in (1, 3, 5, 15, 30, 60)}


def test_okno_eod_na_3m_5m_1m():
    """Na 3m sa zatvára sviečka 15:54–15:57, na 5m 15:50–15:55, na 1m 15:58–15:59; od 18:00 NY sa znova obchoduje."""
    def ms(h, m):
        return int(datetime(2026, 7, 15, h, m, tzinfo=NY).timestamp() * 1000)

    assert not _in_window(ms(15, 51), 3) and _in_window(ms(15, 54), 3)
    assert not _in_window(ms(15, 45), 5) and _in_window(ms(15, 50), 5)
    assert not _in_window(ms(15, 57), 1) and _in_window(ms(15, 58), 1)
    assert _in_window(ms(17, 57), 3) and not _in_window(ms(18, 0), 3)


@pytest.mark.parametrize("wrap", sorted(WRAPS))
@pytest.mark.parametrize("base_key", sorted(BASES))
def test_synteticke_bary(frames, base_key, wrap):
    profile, tf, loose = BASES[base_key]
    stats = _check(base_key, profile, {**loose, **WRAPS[wrap]}, frames[tf], lambda t: frames[int(t.rstrip("m"))], tf,
                   "2026-03-28")
    assert stats["window_bars"] > 100, stats
    assert stats["entries"] > 5, stats
    assert stats["base_held"] > 0 and stats["eod_closes"] > 0, stats
    if (base_key, wrap) == ("noanet", "limitka_dlha"):
        assert stats["eod_cancels"] > 0, stats      # čakajúca limitka o 15:59 — zrušená, nič nečaká


_FIRST = {"ibsentrynet": "IBS_Entry_Zone", "vwaporbnet": "VWAP_ORB", "vwapadxnet": "VWAP_ADX_Pullback", "noanet": "NOA",
          "tksnet": "TKS"}


@pytest.mark.parametrize("base_key", sorted(_FIRST))
def test_profil_smernice_na_mnq(base_key):
    """Prvé nastavenie zo smernice na MNQ (štvrťrok mimo odloženého roka): EOD zavrie všetko, inak nič nemení."""
    path = PROFILES_DIR / f"SMERNICE_CS_EOD_{_FIRST[base_key]}_1.json"
    assert path.is_file(), path
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["_strategy"] == base_key + "eod"
    data.pop("_strategy")
    tf = int(str(data["_timeframe"]).rstrip("m"))
    try:
        chart = _load("mnq", f"{tf}m")
    except (SystemExit, FileNotFoundError, KeyError) as exc:  # chýbajúce dáta
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        prof = Path(d) / path.name
        prof.write_text(json.dumps(data), encoding="utf-8")
        stats = _check(base_key, str(prof), None, chart, lambda t: _load("mnq", t), tf, "2024-09-04", "2024-12-04")
    assert stats["entries"] > 10, stats
