"""Karta Stratégie (`/api/catalog`): profily po skupinách a najlepší beh stratégie."""

from __future__ import annotations

from pathlib import Path

import pytest

from tester.webapp.api.catalog import equity_curve, explainer_lead, payoff_ratio, profile_group, realized_r, title_metrics
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


def test_karta_ma_popis_z_vysvetlivky_kazdej_strategie():
    """Popis na karte je veta „V jednej vete“ z VYSVETLIVKA.md — má ju každá stratégia v registri."""
    from tradebot.strategies import STRATEGIES

    assert explainer_lead("# X\n\n> V jednej vete: kúpi dno.\n\nďalej") == "kúpi dno."
    assert explainer_lead("> V jednej vete: obchoduje **veľké medzery** a `FVG`.") == "obchoduje veľké medzery a FVG."
    assert explainer_lead("# bez vety") == ""
    chyba = [k for k, s in STRATEGIES.items() if not explainer_lead(s.explainer())]
    assert not chyba, f"stratégie bez vety „V jednej vete“ vo VYSVETLIVKA.md: {chyba}"


# --------------------------------------------------------------------------- #
# hodnotenie stratégie (`/api/catalog/<key>/report`) — okno po kliknutí na kartu
# --------------------------------------------------------------------------- #

def _win(run_id: str, window: str, trades: list[tuple[str, float]], checkup: str | None = None,
         profile: str = "multicharts_mnq_3m"):
    cum, eq = 0.0, []
    for t, v in trades:
        cum += v
        eq.append([t, v, cum])
    rec = _run(run_id, profile, pnl_pct=round(cum, 2))
    rec["settings"]["timerange"] = window
    if checkup:
        rec["settings"]["checkup"] = {"id": checkup, "strategy": "ibs"}
    rec["series"] = {"equity": eq, "market": []}
    return rec


def test_parse_analytika_rozdeli_sekcie_a_posudok_zvlast():
    from tester.webapp.api.catalog_report import parse_analytika

    text = """# Základná analytika — X (`x`)

Zmerané 2026-10-26 na `MNQ/USD` 5m, engine `multicharts`, profil `tester/profiles/SMERNICE_CS_NOA_1.json`.

## V čom je dobrá

- zisková v 5 z 5 referenčných okien

## Kde má chyby

- 81.9 % obchodov končí na čase

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- medián držania 4.5 barov

## Posudok (AI)

1. **Na čo sa to hodí**
<!-- POSUDOK cisla=889ebe26 -->

Áno, použiteľné.

<!-- POSUDOK KONIEC -->
"""
    a = parse_analytika(text)
    assert a["exists"] and a["profile"] == "smernice_cs_noa_1"
    assert a["good"] == ["zisková v 5 z 5 referenčných okien"] and a["bad"] == ["81.9 % obchodov končí na čase"]
    assert a["character"] == "Prerazenie (breakout) (istota dobrá)"
    assert [s["title"] for s in a["sections"]] == ["Charakter"]          # verdikty a posudok idú zvlášť
    assert a["posudok"] == "Áno, použiteľné."
    assert parse_analytika("") == {"exists": False}


def test_chain_trades_vynecha_obchody_z_prekryvu_okien():
    from tester.webapp.api.catalog_report import chain_trades, trade_stats

    a = {"series": {"equity": [["2024-08-01T10:00", 2.0, 2.0], ["2024-09-10T10:00", -1.0, 1.0]]}}
    b = {"series": {"equity": [["2024-09-10T10:00", -1.0, -1.0], ["2024-10-05T10:00", 3.0, 2.0]]}}
    trades = chain_trades([a, None, b])
    assert trades == [("2024-08-01T10:00", 2.0), ("2024-09-10T10:00", -1.0), ("2024-10-05T10:00", 3.0)]
    s = trade_stats(trades)
    assert s["trades"] == 3 and s["pnl_pct"] == 4.0 and s["profit_factor"] == 5.0
    assert s["max_dd_pct"] == 1.0 and s["rr"] == 2.5 and s["loss_streak"] == 1
    assert trade_stats([]) == {}


def test_report_vyberie_najuplnejsi_checkup_a_posklada_vykon(client):
    c, store = client
    w = ("20211001-20221001", "20221001-20231001", "20231001-20241001", "20240904-20250904", "20250904-20260904")
    # úplný checkup (5 okien) vyhrá nad novším neúplným (1 okno)
    for i, win in enumerate(w):
        y = 2022 + i
        store.save(_win(f"20261001-12000{i}-aaaaa{i}", win,
                        [(f"{y}-01-10T15:00:00+00:00", 1.0), (f"{y}-03-10T15:00:00+00:00", -0.5)], checkup="ck-old"))
    store.save(_win("20261002-120000-bbbbbb", w[0], [("2022-01-10T15:00:00+00:00", 9.0)], checkup="ck-new"))

    d = c.get("/api/catalog/ibs/report", params={"profile": "multicharts_mnq_3m"}).json()
    perf = d["performance"]
    assert d["profile"]["name"] == "multicharts_mnq_3m" and d["profile"]["group"] == "repo"
    assert perf["checkup_id"] == "ck-old" and len(perf["windows"]) == 5 and perf["positive_windows"] == 5
    assert perf["stats"]["trades"] == 10 and perf["stats"]["pnl_pct"] == 2.5
    assert [y["year"] for y in perf["years"]] == ["2022", "2023", "2024", "2025", "2026"]
    assert perf["months"]["2022"] == {"01": 1.0, "03": -0.5}
    assert perf["curve"][0][1] == 0.0 and perf["curve"][-1][1] == 2.5
    assert d["runs"]["profile_total"] == 6 and d["runs"]["recent"][0]["id"] == "20261002-120000-bbbbbb"

    # profil bez behov: žiadny výkon, ale okno sa poskladá
    e = c.get("/api/catalog/ibs/report", params={"profile": "golden_coinbase_btcusd_3m"}).json()
    assert e["performance"] is None and e["single"] is None and e["runs"]["profile_total"] == 0
    assert c.get("/api/catalog/neznama/report").status_code == 404


def test_report_dokument_len_zo_zoznamu(client):
    c, _ = client
    d = c.get("/api/catalog/ibs/report").json()
    assert all(x["id"].startswith(("s/", "m/")) for x in d["docs"])
    if d["docs"]:
        first = d["docs"][0]["id"]
        assert c.get("/api/catalog/ibs/doc", params={"id": first}).json()["markdown"]
    assert c.get("/api/catalog/ibs/doc", params={"id": "s/../../../../README.md"}).status_code == 404


def test_realized_r_kde_zatvara_v_nasobkoch_rizika():
    """Long s TP na 0,5 R, short so stopom (−1 R), obchod bez stopu sa nepočíta."""
    t = [
        {"open_rate": 100.0, "close_rate": 105.0, "initial_stop_loss_abs": 90.0, "is_short": False},   # +0,5 R
        {"open_rate": 200.0, "close_rate": 204.0, "initial_stop_loss_abs": 204.0, "is_short": True},   # −1 R
        {"open_rate": 50.0, "close_rate": 51.0, "is_short": False},                                    # bez stopu
        {"open_rate": 10.0, "close_rate": 9.0, "initial_stop_loss_abs": 10.0, "is_short": False},      # nulové riziko
    ]
    r = realized_r(t)
    assert r == {"r_win": 0.5, "r_loss": -1.0, "r_avg": -0.25, "r_n": 2}
    assert realized_r([]) == {}
