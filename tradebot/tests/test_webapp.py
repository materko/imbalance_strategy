"""Webapp pre testerov — metadáta z Pine, ukladanie a vyhľadávanie behov, API.

Samotný Freqtrade sa tu nespúšťa (to je integračný test na minúty); testuje sa
všetko okolo: že formulár dostane všetkých ~110 polí so správnymi typmi, že sa beh
uloží ako git-friendly JSON a nájde podľa parametrov, a že API odmietne zlý config
skôr, než by sa niečo spustilo.
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pytest

from tradebot.core import IBSConfig
from tradebot.strategies.ibs.config import PORT_ONLY_FIELDS
from tradebot.webapp.pine_meta import PORT_GROUP, REMOVED_INPUTS, param_metadata
from tradebot.webapp.store import RunStore, make_run_id, parse_query


# --------------------------------------------------------------------------- #
# pine_meta
# --------------------------------------------------------------------------- #


def test_metadata_covers_every_config_field_except_removed():
    names = {m["name"] for m in param_metadata()}
    expected = {f.name for f in fields(IBSConfig) if f.name not in REMOVED_INPUTS}
    assert names == expected


def test_metadata_types_and_groups():
    by = {m["name"]: m for m in param_metadata()}
    assert by["rrRatio"]["type"] == "float" and by["rrRatio"]["min"] == 0.5 and by["rrRatio"]["max"] == 10.0
    assert by["enableImbEntry"]["type"] == "bool" and by["enableImbEntry"]["default"] is True
    assert by["snapMode"]["options"] == ["Off", "Floor", "Ceil", "Round"]
    assert by["minImbSizePoints"]["type"] == "size" and by["minImbSizePoints"]["pine_unit"] == "abs"
    assert by["minSlDistance"]["type"] == "size" and by["minSlDistance"]["pine_unit"] == "pct"
    assert by["ewLineColor"]["type"] == "color"
    for name in PORT_ONLY_FIELDS:
        assert by[name]["group"] == PORT_GROUP, name
    # titulky a tooltipy prišli z Pine, nie z názvu poľa
    assert by["rrRatio"]["title"] == "Risk:Reward pomer"
    assert "Take Profit" in by["rrRatio"]["tooltip"]
    assert by["sess2TZ"]["group"].endswith("Session 2")


def test_feature_dependencies_reference_real_bool_switches():
    """Tabuľka FEATURES je ručná — každé meno musí existovať, prepínače musia byť bool
    a jedno pole nesmie visieť na dvoch featurách naraz (formulár by nevedel, čo poslúchať)."""
    from tradebot.webapp.pine_meta import FEATURES

    by = {m["name"]: m for m in param_metadata()}
    seen: set[str] = set()
    for feat in FEATURES:
        for sw in feat["switches"]:
            assert by[sw]["type"] == "bool", sw
        if feat.get("show"):
            assert by[feat["show"]]["type"] == "bool"
        for name in feat["params"]:
            assert name in by, name
            assert name not in seen, f"{name} je v dvoch featurách"
            seen.add(name)
    assert by["sess1ZoneStartH"]["depends_on"] == ["sess1On"]
    assert by["srSwingLen"]["depends_on"] == ["enableSrTrading", "showSR"]
    assert by["enableSrTrading"]["show_param"] == "showSR"
    assert by["rrRatio"]["depends_on"] is None and by["rrRatio"]["show_param"] is None


def test_metadata_groups_follow_pine_order():
    groups = []
    for m in param_metadata():
        if m["group"] not in groups:
            groups.append(m["group"])
    assert groups[0].endswith("Obchodovanie")
    assert groups[-1] == PORT_GROUP


# --------------------------------------------------------------------------- #
# store
# --------------------------------------------------------------------------- #


def _record(run_id: str, **over):
    params = IBSConfig().to_dict()
    params.update(over.pop("params", {}))
    rec = {
        "id": run_id, "status": "done", "created": "2026-09-05T10:00:00+00:00", "user": "tester",
        "note": over.pop("note", ""), "settings": {"pair": "BTC/USDT:USDT", "timerange": "20250904-20260904",
                                                   "fee": 0.0005, "wallet": 10000, "profile": "btcusdt_3m_binance_ny"},
        "params": params,
        "result": {"trades": 149, "wins": 60, "losses": 89, "winrate": 40.3, "pnl_abs": 2000.0, "pnl_pct": 20.0,
                   "profit_factor": 1.9, "max_drawdown_pct": 6.7, "break_even_pct": 0.141},
        "series": {"equity": [], "market": []},
    }
    rec.update(over)
    return rec


def test_run_id_is_time_plus_param_fingerprint():
    from datetime import datetime, timezone

    when = datetime(2026, 9, 5, 12, 30, 0, tzinfo=timezone.utc)
    a = make_run_id({"rrRatio": 5}, {"pair": "BTC"}, when)
    b = make_run_id({"rrRatio": 6}, {"pair": "BTC"}, when)
    assert a.startswith("20260905-123000-") and a != b and len(a) == 22


def test_store_roundtrip_is_plain_json(tmp_path: Path):
    store = RunStore(tmp_path)
    rec = _record("20260905-120000-abc123", note="prvy")
    d = store.save(rec, trades=[{"profit_abs": 1.0}], log="log")
    assert (d / "run.json").exists() and (d / "trades.json").exists() and (d / "log.txt").exists()
    assert json.loads((d / "run.json").read_text(encoding="utf-8"))["note"] == "prvy"
    assert store.get(rec["id"])["result"]["trades"] == 149
    assert store.trades(rec["id"]) == [{"profit_abs": 1.0}]
    assert store.log(rec["id"]) == "log"
    assert store.delete(rec["id"]) and store.get(rec["id"]) is None


def test_store_rejects_bad_ids(tmp_path: Path):
    store = RunStore(tmp_path)
    with pytest.raises(ValueError):
        store.save({"id": "../etc"})
    assert store.delete("../etc") is False


def test_search_by_params_results_and_text(tmp_path: Path):
    store = RunStore(tmp_path)
    store.save(_record("20260905-120000-aaaaaa", params={"rrRatio": 5.0, "useStructureFilter": True}, note="NY seansa"))
    store.save(_record("20260905-120001-bbbbbb", params={"rrRatio": 2.5}, result={"trades": 300, "pnl_pct": -5.0, "profit_factor": 0.9}))
    store.save(_record("20260905-120002-cccccc", params={"minSlDistance": {"value": 0.2, "unit": "pct"}},
                       settings={"pair": "ETH/USDT:USDT", "timerange": "x", "fee": 0.0005, "wallet": 10000, "profile": "eth"}))

    ids = lambda q: [r["id"][-6:] for r in store.search(q)]  # noqa: E731
    assert ids("rrRatio>=5") == ["aaaaaa"]
    assert ids("useStructureFilter=true") == ["aaaaaa"]
    assert ids("useStructureFilter=false") == ["cccccc", "bbbbbb"]
    assert ids("pnl>0") == ["cccccc", "aaaaaa"]
    assert ids("pf<1") == ["bbbbbb"]
    assert ids("pair~ETH") == ["cccccc"]
    assert ids("minSlDistance>=0.2") == ["cccccc"]  # SizeSpec sa porovnáva cez value
    assert ids("seansa") == ["aaaaaa"]
    assert ids("rrRatio=2.5 trades>=300") == ["bbbbbb"]
    assert ids("") == ["cccccc", "bbbbbb", "aaaaaa"]
    assert ids("neexistujuce>1") == []


def test_parse_query_tokens():
    assert parse_query('rrRatio>=5 note~"NY seansa" hello') == [
        ("rrRatio", ">=", "5"), ("note", "~", "NY seansa"), ("*", "~", "hello"),
    ]


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #


@pytest.fixture
def client(tmp_path: Path):
    fastapi = pytest.importorskip("fastapi")  # noqa: F841
    from fastapi.testclient import TestClient

    from tradebot.webapp.app import create_app
    from tradebot.webapp.runner import BacktestRunner

    store = RunStore(tmp_path)
    runner = BacktestRunner(store, command_builder=lambda *a: ["python", "-c", "raise SystemExit(0)"])
    return TestClient(create_app(store, runner)), store


def test_meta_endpoint(client):
    c, _ = client
    m = c.get("/api/meta").json()
    assert len(m["params"]) == len(param_metadata())
    assert "golden_binance_btcusdt_3m" in m["profiles"] and m["profile_titles"]["golden_binance_btcusdt_3m"]
    assert m["defaults"]["rrRatio"] == 1.0


def test_profile_endpoint(client):
    c, _ = client
    p = c.get("/api/profiles/golden_binance_btcusdt_3m").json()
    assert p["instrument"] == "btcusdt_binance"
    assert p["params"]["legacyPineSizing"] is True and p["params"]["tradeDirection"] == "Long only"
    assert p["params"]["tickDollarValue"] == 0.5  # presne to, s čím bežal TradingView
    assert c.get("/api/profiles/neexistuje").status_code == 404
    # archivované profily sa berú cestou v repozitári, nič mimo neho
    arch = c.get("/api/profiles/docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json").json()
    assert arch["instrument"] == "btcusdt_binance" and arch["params"]["rrRatio"] == 5.0
    assert c.get("/api/profiles/../../x.json").status_code == 404
    assert c.get("/api/profiles/docs/WEBAPP.md").status_code == 404
    assert c.get("/api/meta").json()["profile_instruments"]["multicharts_mnq_3m"] == "mnq"


def test_submit_rejects_invalid_config_and_pair(client):
    c, _ = client
    base = {"params": IBSConfig().to_dict(), "pair": "BTC/USDT:USDT", "timerange": "20260801-20260901"}
    assert c.post("/api/runs", json={**base, "params": {**base["params"], "rrRatio": 99}}).status_code == 422
    assert c.post("/api/runs", json={**base, "pair": "XRP/USDT:USDT"}).status_code == 422
    assert c.post("/api/runs", json={**base, "timerange": "2026-08"}).status_code == 422
    assert c.post("/api/runs", json={**base, "timerange": "20260901-20260801"}).status_code == 422


def test_runs_listing_and_detail(client):
    c, store = client
    store.save(_record("20260905-120000-aaaaaa", params={"rrRatio": 5.0}), trades=[{"profit_abs": 3.0}], log="x")
    lst = c.get("/api/runs", params={"q": "rrRatio=5"}).json()
    assert lst["total"] == 1 and lst["runs"][0]["overrides"] == {"rrRatio": 5.0}
    det = c.get("/api/runs/20260905-120000-aaaaaa").json()
    assert det["record"]["overrides"] == {"rrRatio": 5.0} and det["trades"] == [{"profit_abs": 3.0}]
    assert c.get("/api/runs/20260905-120000-aaaaaa/log").text == "x"
    prof = c.get("/api/runs/20260905-120000-aaaaaa/profile.json").json()
    assert prof["_instrument"] == "btcusdt_binance" and prof["rrRatio"] == 5.0
    assert c.delete("/api/runs/20260905-120000-aaaaaa").json() == {"ok": True}
    assert c.get("/api/runs/20260905-120000-aaaaaa").status_code == 404


def test_build_command_passes_timeframe_and_drops_useless_detail():
    from tradebot.webapp.runner import build_command, tf_minutes

    base = {"pair": "BTC/USDT:USDT", "timerange": "20260801-20260901", "wallet": 10000, "fee": 0.0005}
    cmd = build_command("py", Path("p.json"), {**base, "timeframe": "15m", "timeframe_detail": "1m"})
    assert cmd[cmd.index("--timeframe") + 1] == "15m" and "--timeframe-detail" in cmd
    cmd = build_command("py", Path("p.json"), {**base, "timeframe": "1m", "timeframe_detail": "1m"})
    assert "--timeframe-detail" not in cmd  # detail musí byť jemnejší než TF grafu
    cmd = build_command("py", Path("p.json"), base)
    assert cmd[cmd.index("--timeframe") + 1] == "3m"
    assert tf_minutes("1h") == 60 and tf_minutes("3m") == 3


def test_submit_validates_timeframe(client, monkeypatch):
    import tradebot.webapp.app as app_mod

    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["1m", "3m", "5m"])
    c, _ = client
    base = {"params": IBSConfig().to_dict(), "pair": "BTC/USDT:USDT", "timerange": "20260801-20260901"}
    assert c.post("/api/runs", json={**base, "timeframe": "2m"}).status_code == 422
    assert c.post("/api/runs", json={**base, "timeframe": "15m"}).status_code == 422  # nie sú dáta
    job = c.post("/api/runs", json={**base, "timeframe": "5m"}).json()
    assert job["settings"]["timeframe"] == "5m" and job["settings"]["timeframe_detail"] == "1m"
    job = c.post("/api/runs", json={**base, "timeframe": "1m"}).json()
    assert job["settings"]["timeframe_detail"] is None
    assert c.post("/api/runs", json=base).json()["settings"]["timeframe"] == "3m"


def test_submit_uses_tester_name_from_request(client, monkeypatch):
    """Meno z hlavičky stránky ide k behu; bez neho sa použije predvolené."""
    import tradebot.webapp.app as app_mod

    monkeypatch.setattr(app_mod, "current_user", lambda: "predvolene")
    c, _ = client
    base = {"params": IBSConfig().to_dict(), "pair": "BTC/USDT:USDT", "timerange": "20260801-20260901"}
    job = c.post("/api/runs", json={**base, "user": "  Jana  "}).json()
    assert job["user"] == "Jana"
    job2 = c.post("/api/runs", json={**base, "user": ""}).json()
    assert job2["user"] == "predvolene"
    assert c.post("/api/runs", json={**base, "user": "x" * 81}).status_code == 422


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #


def test_cli_parse_set_values():
    from tradebot.webapp.cli import parse_set

    assert parse_set("rrRatio=5") == ("rrRatio", 5)
    assert parse_set("useStructureFilter=true") == ("useStructureFilter", True)
    assert parse_set("minSlDistance=0.2@pct") == ("minSlDistance", {"value": 0.2, "unit": "pct"})
    assert parse_set("sess2TZ=America/New_York") == ("sess2TZ", "America/New_York")
    assert parse_set('minSlDistance={"value": 1, "unit": "atr"}') == ("minSlDistance", {"value": 1, "unit": "atr"})
    assert parse_set("tickDollarValue=null") == ("tickDollarValue", None)
    with pytest.raises(SystemExit):
        parse_set("bez_rovnasa")


def test_cli_list_and_show_read_the_store(tmp_path: Path, monkeypatch, capsys):
    import tradebot.webapp.cli as cli
    import tradebot.webapp.store as store_mod

    store = RunStore(tmp_path)
    store.save(_record("20260905-120000-aaaaaa", params={"rrRatio": 5.0}, note="baseline"))
    monkeypatch.setattr(store_mod, "RUNS_DIR", tmp_path)

    assert cli.main(["list", "rrRatio=5"]) == 0
    out = capsys.readouterr().out
    assert "20260905-120000-aaaaaa" in out and "break-even 0.1410 %" in out and "baseline" in out

    assert cli.main(["show", "20260905-120000-aaaaaa"]) == 0
    out = capsys.readouterr().out
    assert '"rrRatio": 5.0' in out
    with pytest.raises(SystemExit):
        cli.main(["show", "neexistuje"])
