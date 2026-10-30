"""Karta Stratégie (`/api/catalog`): profily po skupinách a najlepší beh stratégie."""

from __future__ import annotations

from pathlib import Path

import pytest

from tester.webapp.api.catalog import equity_curve, payoff_ratio, profile_group, title_metrics
from tester.webapp.store import RunStore


def _run(run_id: str, profile: str, **result):
    res = {"trades": 150, "winrate": 55.0, "pnl_pct": 20.0, "profit_factor": 1.5,
           "max_drawdown_pct": 5.0, "break_even_pct": 0.05, **result}
    return {"id": run_id, "status": "done", "note": "",
            "settings": {"strategy": "ibs", "pair": "BTC/USDT:USDT", "timeframe": "3m",
                         "timerange": "20250904-20260904", "profile": profile},
            "params": {}, "result": res,
            "series": {"equity": [[i, 1.0, float(i)] for i in range(200)], "market": []}}


@pytest.fixture
def client(tmp_path: Path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.webapp.app import create_app
    from tester.webapp.runner import BacktestRunner

    store = RunStore(tmp_path)
    runner = BacktestRunner(store, command_builder=lambda *a: ["python", "-c", "raise SystemExit(0)"])
    return TestClient(create_app(store, runner)), store


def test_title_metrics_cita_cisla_z_popisu_smernice():
    t = "NOA 1 C# · PF 1,82 · WR 40 % · 156 obch/rok · MNQ 5m · max DD 1 745 $ · posl. rok PF 1,55"
    assert title_metrics(t) == {"pf": 1.82, "winrate": 40.0, "trades_year": 156.0,
                                "max_dd_usd": 1745.0, "pf_last_year": 1.55}
    assert title_metrics("Referenčný golden test") == {}


def test_profile_group_podla_prefixu():
    assert profile_group("PRESIEL_SMERNICAMI_TKS_1", "tks") == "smernica"
    assert profile_group("SMERNICE_CS_NOA_1", "noanet") == "smernica"
    assert profile_group("golden_binance_btcusdt_3m", "ibs") == "repo"


def test_payoff_ratio_z_pf_a_poctu_obchodov():
    # 10 ziskov po 3, 20 strát po 1: PF = 30 / 20 = 1,5, RR = 3
    assert payoff_ratio({"profit_factor": 1.5, "wins": 10, "losses": 20}) == 3.0
    assert payoff_ratio({"profit_factor": 1.5, "wins": 0, "losses": 20}) is None
    assert payoff_ratio({"profit_factor": 1.5}) is None


def test_equity_curve_berie_sucet_a_preriedi():
    rec = {"series": {"equity": [[i, 9.0, float(i)] for i in range(100)]}}
    eq = equity_curve(rec, points=10)
    assert len(eq) == 10 and eq[0] == 0.0 and eq[-1] == 99.0
    assert equity_curve(None) == [] and equity_curve({"series": {}}) == []


def test_catalog_vyberie_najlepsi_beh_a_priradi_ho_profilu(client):
    c, store = client
    # PF 3453 pri pár obchodoch nie je edge — sito ho vynechá, aj keď má najvyšší zisk
    store.save(_run("20260905-120000-aaaaaa", "golden_binance_btcusdt_3m", pnl_pct=900.0, profit_factor=3453.0))
    store.save(_run("20260905-120001-bbbbbb", "tradebot/strategies/ibs/configs/golden_binance_btcusdt_3m.json",
                    pnl_pct=30.0, max_drawdown_pct=5.0))
    store.save(_run("20260905-120002-cccccc", "multicharts_mnq_3m", pnl_pct=10.0, max_drawdown_pct=5.0))
    store.save(_run("20260905-120003-dddddd", "multicharts_mnq_3m", pnl_pct=50.0, trades=10))   # málo obchodov

    rows = {r["key"]: r for r in c.get("/api/catalog").json()["strategies"]}
    ibs = rows["ibs"]
    assert ibs["runs"] == 4 and ibs["last_run"] == "20260905-120003-dddddd"
    assert ibs["best"]["id"] == "20260905-120001-bbbbbb"
    assert ibs["best"]["profile"] == "golden_binance_btcusdt_3m"
    assert len(ibs["best"]["equity"]) == 48 and ibs["best"]["equity"][-1] == 199.0

    prof = {p["name"]: p for p in ibs["profiles"]}
    assert prof["golden_binance_btcusdt_3m"]["group"] == "repo"
    assert prof["golden_binance_btcusdt_3m"]["best_run"]["id"] == "20260905-120001-bbbbbb"   # cesta aj meno
    assert prof["multicharts_mnq_3m"]["best_run"]["id"] == "20260905-120002-cccccc"
    assert prof["golden_coinbase_btcusd_3m"]["best_run"] is None
    # stratégia bez behov v histórii je v katalógu tiež, len bez najlepšieho behu
    assert rows["orb"]["best"] is None and rows["orb"]["runs"] == 0
