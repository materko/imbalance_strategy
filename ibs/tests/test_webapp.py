"""Webapp pre testerov — metadáta z Pine, ukladanie a vyhľadávanie behov, API.

Samotný Freqtrade sa tu nespúšťa (to je integračný test na minúty); testuje sa
všetko okolo: že formulár dostane všetkých ~110 polí so správnymi typmi, že sa beh
uloží ako git-friendly JSON a nájde podľa parametrov, a že API odmietne zlý config
skôr, než by sa niečo spustilo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ibs.core import IBSConfig
from ibs.core.config import PORT_ONLY_FIELDS
from ibs.webapp.pine_meta import PORT_GROUP, REMOVED_INPUTS, param_metadata
from ibs.webapp.store import RunStore, make_run_id, parse_query


# --------------------------------------------------------------------------- #
# pine_meta
# --------------------------------------------------------------------------- #


def test_metadata_covers_every_config_field_except_removed():
    names = {m["name"] for m in param_metadata()}
    expected = {f for f in IBSConfig.__dataclass_fields__ if f not in REMOVED_INPUTS}
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
    from ibs.webapp.pine_meta import FEATURES

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

    from ibs.webapp.app import create_app
    from ibs.webapp.runner import BacktestRunner

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
    arch = c.get("/api/profiles/docs/profily_archiv/btcusdt_3m_binance_ny_sl_risk1.json").json()
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
    from ibs.webapp.runner import build_command, tf_minutes

    base = {"pair": "BTC/USDT:USDT", "timerange": "20260801-20260901", "wallet": 10000, "fee": 0.0005}
    cmd = build_command("py", Path("p.json"), {**base, "timeframe": "15m", "timeframe_detail": "1m"})
    assert cmd[cmd.index("--timeframe") + 1] == "15m" and "--timeframe-detail" in cmd
    cmd = build_command("py", Path("p.json"), {**base, "timeframe": "1m", "timeframe_detail": "1m"})
    assert "--timeframe-detail" not in cmd  # detail musí byť jemnejší než TF grafu
    cmd = build_command("py", Path("p.json"), base)
    assert cmd[cmd.index("--timeframe") + 1] == "3m"
    assert tf_minutes("1h") == 60 and tf_minutes("3m") == 3


def test_submit_validates_timeframe(client, monkeypatch):
    import ibs.webapp.app as app_mod

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
    import ibs.webapp.app as app_mod

    monkeypatch.setattr(app_mod, "current_user", lambda: "predvolene")
    c, _ = client
    base = {"params": IBSConfig().to_dict(), "pair": "BTC/USDT:USDT", "timerange": "20260801-20260901"}
    job = c.post("/api/runs", json={**base, "user": "  Jana  "}).json()
    assert job["user"] == "Jana"
    job2 = c.post("/api/runs", json={**base, "user": ""}).json()
    assert job2["user"] == "predvolene"
    assert c.post("/api/runs", json={**base, "user": "x" * 81}).status_code == 422


# --------------------------------------------------------------------------- #
# Spot vs futures
# --------------------------------------------------------------------------- #


def test_spot_pair_allows_only_longs_without_leverage():
    """Na spote burza nemá čo požičať — short ani páka sa nedajú obchodovať,
    takže beh, ktorý ich má v configu, sa nesmie ani spustiť."""
    from ibs.webapp.runner import check_market_rules

    params = IBSConfig().to_dict()
    check_market_rules("BTC/USDT:USDT", {**params, "tradeDirection": "Both", "leverage": 10})  # futures: v poriadku
    check_market_rules("BTC/USDT", {**params, "tradeDirection": "Long only", "leverage": 1})

    with pytest.raises(ValueError, match="shorty"):
        check_market_rules("BTC/USDT", {**params, "tradeDirection": "Both", "leverage": 1})
    with pytest.raises(ValueError, match="páka"):
        check_market_rules("ETH/USDT", {**params, "tradeDirection": "Long only", "leverage": 5})


def test_spot_pair_runs_with_spot_config_and_file_layout():
    from ibs.webapp.chart import pair_file
    from ibs.webapp.runner import build_command

    base = {"timerange": "20250101-20250201", "wallet": 10000, "fee": 0.0005, "timeframe": "3m"}
    spot = build_command("py", Path("p.json"), {**base, "pair": "BTC/USDT"})
    futures = build_command("py", Path("p.json"), {**base, "pair": "BTC/USDT:USDT"})
    assert spot[spot.index("--config") + 1].endswith("config.binance.spot.json")
    assert futures[futures.index("--config") + 1].endswith("config.binance.json")

    assert pair_file("BTC/USDT", "3m").name == "BTC_USDT-3m.feather"
    assert pair_file("BTC/USDT:USDT", "3m").name == "BTC_USDT_USDT-3m-futures.feather"
    assert pair_file("BTC/USDT", "3m").parent.name == "binance"
    assert pair_file("BTC/USDT:USDT", "3m").parent.name == "futures"


def test_instrument_knows_its_market_and_exchange_name():
    from ibs.core.types import INSTRUMENTS

    perp, spot = INSTRUMENTS["btcusdt_binance"], INSTRUMENTS["btcusdt_binance_spot"]
    assert (perp.exchange_symbol, perp.market, perp.is_spot) == ("BTCUSDT.P", "futures", False)
    assert (spot.exchange_symbol, spot.market, spot.is_spot) == ("BTCUSDT", "spot", True)


def test_submit_rejects_shorts_on_spot(client, monkeypatch):
    import ibs.webapp.app as app_mod

    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["1m", "3m"])
    c, _ = client
    body = {"params": {**IBSConfig().to_dict(), "tradeDirection": "Both"}, "pair": "BTC/USDT",
            "timerange": "20260801-20260901"}
    r = c.post("/api/runs", json=body)
    assert r.status_code == 422 and "spotový" in r.json()["detail"]
    ok = {**body, "params": {**IBSConfig().to_dict(), "tradeDirection": "Long only", "leverage": 1}}
    assert c.post("/api/runs", json=ok).status_code == 200


# --------------------------------------------------------------------------- #
# Vlastné profily testera
# --------------------------------------------------------------------------- #


@pytest.fixture
def own_profiles(tmp_path: Path, monkeypatch):
    """Vlastné profily do tmp adresára, nech testy nepíšu do repozitára."""
    import ibs.webapp.profiles as profiles_mod

    d = tmp_path / "profiles"
    monkeypatch.setattr(profiles_mod, "PROFILES_DIR", d)
    return d


def test_save_run_as_profile_keeps_only_deviations(client, own_profiles):
    c, store = client
    store.save(_record("20260905-120000-aaaaaa", params={"rrRatio": 5.0}))
    r = c.post("/api/profiles", json={"name": "moj_rr5", "from_run": "20260905-120000-aaaaaa",
                                      "note": "RR 5"})
    assert r.status_code == 200 and r.json()["user_profiles"] == ["moj_rr5"]

    data = json.loads((own_profiles / "moj_rr5.json").read_text(encoding="utf-8"))
    assert data["_instrument"] == "btcusdt_binance" and data["rrRatio"] == 5.0
    assert "RR 5" in data["_comment"] and "20260905-120000-aaaaaa" in data["_comment"]
    assert "enableImbEntry" not in data  # Pine default sa neukladá

    p = c.get("/api/profiles/moj_rr5").json()
    assert p["params"]["rrRatio"] == 5.0 and p["instrument"] == "btcusdt_binance" and p["kind"] == "user"
    meta = c.get("/api/meta").json()
    assert "moj_rr5" in meta["profiles"] and meta["user_profiles"] == ["moj_rr5"]


def test_profile_keeps_the_whole_setup_of_the_run(client, own_profiles):
    """Profil drží aj nastavenia behu — TF (limity `*MaxBars` sú v baroch), obdobie,
    poplatok, peňaženku a 1m detail; inak by povedal „ako", ale nie „na čom"."""
    c, store = client
    rec = _record("20260905-120000-aaaaaa", params={"rrRatio": 5.0})
    rec["settings"].update(timeframe="5m", timeframe_detail="1m")
    store.save(rec)
    c.post("/api/profiles", json={"name": "moj_5m", "from_run": "20260905-120000-aaaaaa"})
    data = json.loads((own_profiles / "moj_5m.json").read_text(encoding="utf-8"))
    assert data["_timeframe"] == "5m" and data["_timerange"] == "20250904-20260904"
    assert data["_fee"] == 0.0005 and data["_wallet"] == 10000 and data["_detail"] == "1m"
    got = c.get("/api/profiles/moj_5m").json()
    assert got["timeframe"] == "5m" and got["settings"]["timerange"] == "20250904-20260904"

    # profil sa dá uložiť aj priamo z formulára, s vlastným TF a nastaveniami
    c.post("/api/profiles", json={"name": "z_formulara", "params": IBSConfig().to_dict(),
                                  "instrument": "btcusdt_binance", "timeframe": "15m",
                                  "timerange": "20240101-20240301", "fee": 0, "wallet": 400000,
                                  "timeframe_detail": None})
    got = c.get("/api/profiles/z_formulara").json()
    assert got["settings"] == {"timeframe": "15m", "timerange": "20240101-20240301",
                               "fee": 0, "wallet": 400000, "detail": False}
    # profil repozitára nastavenia behu nemá — formulár si vtedy nechá, čo v ňom je
    assert c.get("/api/profiles/golden_binance_btcusdt_3m").json()["settings"] == {}


def test_profile_save_rejects_bad_name_and_collisions(client, own_profiles):
    c, store = client
    store.save(_record("20260905-120000-aaaaaa"))
    body = {"name": "moj", "from_run": "20260905-120000-aaaaaa"}
    assert c.post("/api/profiles", json={**body, "name": "má medzeru"}).status_code == 422
    assert c.post("/api/profiles", json={**body, "name": "../uteka"}).status_code == 422
    assert c.post("/api/profiles", json={**body, "name": "golden_binance_btcusdt_3m"}).status_code == 422
    assert c.post("/api/profiles", json={"name": "moj"}).status_code == 422  # ani beh, ani parametre
    assert c.post("/api/profiles", json={**body, "from_run": "20260101-000000-ffffff"}).status_code == 404
    assert c.post("/api/profiles", json=body).status_code == 200
    assert c.post("/api/profiles", json=body).status_code == 409
    assert c.post("/api/profiles", json={**body, "overwrite": True}).status_code == 200


def test_profile_rename_and_delete_only_own(client, own_profiles):
    c, store = client
    store.save(_record("20260905-120000-aaaaaa", params={"rrRatio": 5.0}))
    c.post("/api/profiles", json={"name": "moj", "from_run": "20260905-120000-aaaaaa"})

    assert c.patch("/api/profiles/moj", json={"name": "moj_lepsi"}).json()["user_profiles"] == ["moj_lepsi"]
    assert (own_profiles / "moj_lepsi.json").exists() and not (own_profiles / "moj.json").exists()
    assert c.patch("/api/profiles/golden_binance_btcusdt_3m", json={"name": "x"}).status_code == 422
    assert c.patch("/api/profiles/neexistuje", json={"name": "x"}).status_code == 404
    assert c.patch("/api/profiles/moj_lepsi", json={"name": "golden_binance_btcusdt_3m"}).status_code == 422

    assert c.delete("/api/profiles/golden_binance_btcusdt_3m").status_code == 422
    assert c.delete("/api/profiles/neexistuje").status_code == 404
    assert c.delete("/api/profiles/moj_lepsi").json()["user_profiles"] == []
    assert not (own_profiles / "moj_lepsi.json").exists()


def test_profile_params_are_validated_before_save(own_profiles):
    from ibs.core.config import ConfigError
    from ibs.webapp import profiles

    params = IBSConfig().to_dict()
    with pytest.raises(ConfigError):
        profiles.save("zly", {**params, "rrRatio": 99}, "btcusdt_binance")
    with pytest.raises(profiles.ProfileError):
        profiles.save("zly", params, "neznamy_nastroj")
    assert profiles.user_names() == []


def test_git_commit_message_counts_runs_and_profiles():
    from ibs.webapp.gitsync import _message

    assert _message([" M platforms/freqtrade/user_data/runs/a/run.json"]) == "Pridaj 1 beh backtestu z webapp"
    assert _message(["?? platforms/freqtrade/user_data/profiles/moj.json"]) == "Pridaj 1 profil z webapp"
    mixed = _message([" M platforms/freqtrade/user_data/runs/a/run.json",
                      "?? platforms/freqtrade/user_data/runs/b/run.json",
                      "?? platforms/freqtrade/user_data/profiles/moj.json"])
    assert mixed == "Pridaj 2 behy backtestu a 1 profil z webapp"


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #


def test_cli_parse_set_values():
    from ibs.webapp.cli import parse_set

    assert parse_set("rrRatio=5") == ("rrRatio", 5)
    assert parse_set("useStructureFilter=true") == ("useStructureFilter", True)
    assert parse_set("minSlDistance=0.2@pct") == ("minSlDistance", {"value": 0.2, "unit": "pct"})
    assert parse_set("sess2TZ=America/New_York") == ("sess2TZ", "America/New_York")
    assert parse_set('minSlDistance={"value": 1, "unit": "atr"}') == ("minSlDistance", {"value": 1, "unit": "atr"})
    assert parse_set("tickDollarValue=null") == ("tickDollarValue", None)
    with pytest.raises(SystemExit):
        parse_set("bez_rovnasa")


def test_cli_list_and_show_read_the_store(tmp_path: Path, monkeypatch, capsys):
    import ibs.webapp.cli as cli
    import ibs.webapp.store as store_mod

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
