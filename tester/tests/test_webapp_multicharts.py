"""Webapp „burza" MultiCharts: ponuka párov, sviečky z 1m, beh cez emulátor, archívny nástroj."""

from __future__ import annotations

from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from tradebot.core.types import INSTRUMENTS
from tester.webapp import chart as chart_mod
from tester.webapp import runner as runner_mod

MIN = 60_000
T0 = 1_736_121_600_000  # 2025-01-06 00:00 UTC
INST = INSTRUMENTS["nas100_dukascopy"]


def m1(n: int, start_ms: int = T0) -> "pd.DataFrame":
    return pd.DataFrame({
        "date": [pd.Timestamp(start_ms + i * MIN, unit="ms", tz="UTC") for i in range(n)],
        "open": [100.0 + i for i in range(n)], "high": [101.0 + i for i in range(n)],
        "low": [99.0 + i for i in range(n)], "close": [100.5 + i for i in range(n)], "volume": [1.0] * n,
    })


@pytest.fixture
def mc_data(tmp_path: Path, monkeypatch) -> Path:
    mc_dir = tmp_path / "data" / "multicharts"
    (mc_dir / INST.data_source).mkdir(parents=True)
    path = mc_dir / INST.data_source / f"{INST.data_stem}-1m.feather"
    m1(60).to_feather(path)
    monkeypatch.setattr(runner_mod, "MC_DIR", mc_dir)
    monkeypatch.setattr(chart_mod, "MC_DIR", mc_dir)
    # Binance adresáre nech sú prázdne, aby test videl len MultiCharts pár
    monkeypatch.setattr(runner_mod, "DATA_DIR", tmp_path / "data" / "binance" / "futures")
    monkeypatch.setattr(runner_mod, "SPOT_DIR", tmp_path / "data" / "binance")
    monkeypatch.setattr(chart_mod, "DATA_DIR", tmp_path / "data" / "binance" / "futures")
    monkeypatch.setattr(chart_mod, "SPOT_DIR", tmp_path / "data" / "binance")
    chart_mod._frame.cache_clear()
    return path


def test_instrument_multicharts_ma_stem_a_symbol_pre_ponuku():
    assert INST.symbol == "NAS100/USD" and INST.venue == "multicharts"
    assert INST.data_stem == "NAS100_USD" and INST.exchange_symbol == "NAS100"
    assert INSTRUMENTS["btcusdt_binance"].data_stem == "BTC_USDT_USDT"
    assert runner_mod.is_multicharts_pair("NAS100/USD") and not runner_mod.is_multicharts_pair("BTC/USDT:USDT")
    assert not runner_mod.is_multicharts_pair("NEZNAMY/PAR")


def test_ponuka_parov_obsahuje_multicharts_par_s_rozsahom(mc_data):
    pairs = runner_mod.available_pairs()
    assert [p["pair"] for p in pairs] == ["NAS100/USD"]
    p = pairs[0]
    assert p["exchange"] == "multicharts" and p["instrument"] == "nas100_dukascopy" and p["market"] == "futures"
    assert p["exchange_symbol"] == "NAS100" and p["from"] == "2025-01-06" and p["bars"] == 60
    assert p["has_1m"] and p["has_5m"] and "3m" in p["timeframes"]


def test_sviecky_multicharts_paru_sa_skladaju_z_1m(mc_data):
    assert chart_mod.pair_file("NAS100/USD", "3m") == mc_data
    assert chart_mod.available_timeframes("NAS100/USD") == list(chart_mod.TIMEFRAMES)
    c1 = chart_mod.candles("NAS100/USD", "1m", T0, T0 + 6 * MIN)
    c3 = chart_mod.candles("NAS100/USD", "3m", T0, T0 + 6 * MIN)
    assert len(c1["t"]) == 6 and len(c3["t"]) == 2
    assert c3["o"][0] == 100.0 and c3["h"][0] == 103.0 and c3["l"][0] == 99.0 and c3["c"][0] == 102.5 and c3["v"][0] == 3.0


def test_beh_na_burze_multicharts_ide_cez_emulator_a_ulozi_sa(mc_data, tmp_path: Path, monkeypatch):
    from tradebot.adapters.multicharts.emulator import EmulationResult, EmuTrade
    from tradebot.core.types import Direction
    from tester.webapp.store import RunStore

    monkeypatch.setattr(runner_mod, "TMP_PROFILES", tmp_path / "profiles")
    calls = {}

    def fake_emulate(cfg, inst, m1_df, chart_tf, *, from_ms=None, to_ms=None, log=None, should_stop=None, registry=None, spec=None):
        calls.update(inst=inst.symbol, chart_tf=chart_tf, from_ms=from_ms, to_ms=to_ms, rows=len(m1_df))
        log("emulacia: test")
        t = EmuTrade("LONG_1", Direction.LONG, qty=2.0, entry=100.0, open_ms=T0 + 3 * MIN, stop_initial=99.0,
                     take_profit=102.0, market=False, stop_last=99.0, exit=102.0, close_ms=T0 + 9 * MIN,
                     reason="take_profit", max_price=102.0, min_price=99.5)
        result = EmulationResult(trades=[t], bars=20, first_ms=T0, last_ms=T0 + 57 * MIN, first_close=100.5,
                                 last_close=159.5, ambiguous=0, daily_closes=[(T0, 159.5)])
        from tradebot.adapters.multicharts.runner import MCRunner

        return result, MCRunner(cfg, inst, chart_tf)

    from tradebot.adapters.multicharts import emulator

    monkeypatch.setattr(emulator, "emulate", fake_emulate)

    store = RunStore(tmp_path / "runs")
    br = runner_mod.BacktestRunner(store)
    params = runner_mod.default_params("docs/profily_archiv/ibs/nas100_dukas_3m.json")[0]
    settings = {"strategy": "ibs", "pair": "NAS100/USD", "timeframe": "3m", "timerange": "20250106-20250107",
                "fee": 0.001, "wallet": 10000.0, "timeframe_detail": "1m", "profile": "nas100_dukas_3m"}
    # nie submit(): ten by spustil pracovné vlákno, ktoré by beh vykonalo súbežne s priamym _run
    from tester.webapp.store import make_run_id

    job = runner_mod.Job(id=make_run_id(params, settings), params=params, settings=settings, note="test", user="t")
    br._run(job)

    assert job.status == "done", job.error
    assert calls["inst"] == "NAS100/USD" and calls["chart_tf"] == 3 and calls["rows"] == 60
    assert calls["from_ms"] == T0 and calls["to_ms"] == T0 + 86_400_000
    rec = store.get(job.id)
    res = rec["result"]
    assert res["trades"] == 1 and res["wins"] == 1 and res["engine"] == "multicharts-emulator"
    assert res["pnl_abs"] == pytest.approx(4.0 - 0.001 * (200 + 204), abs=0.01) and res["stake_currency"] == "USD"
    trades = store.trades(job.id)
    assert trades[0]["enter_tag"] == "LONG_1" and trades[0]["exit_reason"] == "take_profit"
    assert store.has_chart(job.id) and "emulacia: test" in store.log(job.id)


def test_dukas_import_zapise_rocne_subory(tmp_path: Path, capsys):
    """Cesta pre Tester: surový export -> ročné feather súbory v archíve MultiCharts."""
    from tester.dukas_import import load_dukas_frame, main, write_years

    csv = tmp_path / "X_M1.csv"
    csv.write_text(
        "dt,o,h,l,c,vol\n"
        "2024-12-31 23:59:00,100,101,99,100.5,1\n"
        "2025-01-01 00:00:00,100.5,100.5,100.5,100.5,0\n"   # vypchavka
        "2025-01-01 00:01:00,100.6,100.9,100.4,100.7,2\n"
        "2026-01-01 00:00:00,110,111,109,110.5,3\n",
        encoding="utf-8",
    )
    df = load_dukas_frame(csv)
    assert len(df) == 3 and str(df["date"].dt.tz) == "UTC"
    files = write_years(df, "NAS100_USD", archive=tmp_path / "arch", from_year=2025, verbose=False)
    assert [f.name for f in files] == ["NAS100_USD-1m.2025.feather", "NAS100_USD-1m.2026.feather"]
    assert len(pd.read_feather(files[0])) == 1

    rc = main([str(csv), "--symbol", "NAS100", "--target", "tester",
               "--archive", str(tmp_path / "arch2"), "--no-merge"])
    assert rc == 0
    # zdroj je adresar: <archiv>/<zdroj>/<PAR>-1m.<rok>.feather
    out = tmp_path / "arch2" / INST.data_source
    assert sorted(p.name for p in out.glob("*.feather")) == [
        "NAS100_USD-1m.2024.feather", "NAS100_USD-1m.2025.feather", "NAS100_USD-1m.2026.feather"]
    assert "zapisanych 3 rocnych suborov" in capsys.readouterr().err


def test_dukas_import_odmietne_neznamy_symbol_bez_hodnoty_bodu(tmp_path: Path, capsys):
    """Bez Big Point Value by sizing v Testeri a v MultiCharts nebol ten istý."""
    from tester.dukas_import import main

    csv = tmp_path / "Y_M1.csv"
    csv.write_text("dt,o,h,l,c,vol\n2025-01-01 00:00:00,1,2,0.5,1.5,1\n", encoding="utf-8")
    assert main([str(csv), "--symbol", "NECOTAKE", "--target", "tester"]) == 1
    err = capsys.readouterr().err
    assert "--point-value" in err and "nas100_dukascopy" in err


def test_dukas_import_prida_novy_symbol_a_kostru_profilu(tmp_path: Path):
    """Nový symbol = riadok v tabuľke Dukascopy + profil, ktorý sa dá rovno spustiť."""
    import json

    from tradebot.core.types import INSTRUMENTS, dukascopy_specs
    from tester import dukas_import as di

    registry = tmp_path / "instruments_dukascopy.json"
    registry.write_text("{}", encoding="utf-8")
    try:
        key, inst = di.register_symbol("EURUSD", point_value=100000.0, tick_size=0.00001,
                                       registry=registry)
        assert key == "eurusd_dukascopy" and inst.symbol == "EURUSD/USD"
        assert inst.venue == "multicharts" and inst.has_real_volume is False
        assert json.loads(registry.read_text(encoding="utf-8"))["eurusd_dukascopy"]["point_value"] == 100000.0
        assert di.resolve_symbol("EURUSD") == (key, inst)

        profile = di.write_profile_skeleton(key, inst, out_dir=tmp_path)
        data = json.loads(profile.read_text(encoding="utf-8"))
        assert profile.name == "eurusd_dukas_3m.json"
        assert data["_instrument"] == key and data["tickDollarValue"] == pytest.approx(1.0)
        assert any("atr" in line for line in data["_comment"])
    finally:
        INSTRUMENTS.pop("eurusd_dukascopy", None)
        INSTRUMENTS.update(dukascopy_specs())
