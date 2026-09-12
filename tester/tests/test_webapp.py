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
from tester.webapp.param_meta import INERT_INPUTS, PORT_GROUP, REMOVED_INPUTS, param_metadata
from tester.webapp.store import RunStore, make_run_id, parse_query


# --------------------------------------------------------------------------- #
# param_meta
# --------------------------------------------------------------------------- #


def test_metadata_covers_every_config_field_except_removed():
    names = {m["name"] for m in param_metadata()}
    expected = {f.name for f in fields(IBSConfig) if f.name not in REMOVED_INPUTS | INERT_INPUTS}
    # alert* polia v configu ostávajú (parita s TV panelom), len sa neponúkajú
    assert INERT_INPUTS < {f.name for f in fields(IBSConfig)}
    assert names == expected


def test_metadata_types_and_groups():
    by = {m["name"]: m for m in param_metadata()}
    assert by["rrRatio"]["type"] == "float" and by["rrRatio"]["min"] == 0.5 and by["rrRatio"]["max"] == 10.0
    assert by["enableImbEntry"]["type"] == "bool" and by["enableImbEntry"]["default"] is True
    assert by["snapMode"]["options"] == ["Off", "Floor", "Ceil", "Round"]
    assert by["minImbSizePoints"]["type"] == "size" and by["minImbSizePoints"]["base_unit"] == "abs"
    assert by["minSlDistance"]["type"] == "size" and by["minSlDistance"]["base_unit"] == "pct"
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
    from tester.webapp.param_meta import FEATURES

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

    from tester.webapp.app import create_app
    from tester.webapp.runner import BacktestRunner

    store = RunStore(tmp_path)
    runner = BacktestRunner(store, command_builder=lambda *a: ["python", "-c", "raise SystemExit(0)"])
    return TestClient(create_app(store, runner)), store


def test_history_pages_apply_filter_before_offset(client):
    c, store = client
    for i in range(6):
        store.save(_record(f"20260905-12000{i}-abc123", note="selected" if i % 2 else "other"))
    expected = [r["id"] for r in store.search("note=selected")]
    first = c.get("/api/runs", params={"q": "note=selected", "limit": 2}).json()
    second = c.get("/api/runs", params={"q": "note=selected", "limit": 2, "offset": 2}).json()
    assert first["total"] == second["total"] == 3
    assert [r["id"] for r in first["runs"] + second["runs"]] == expected
    assert c.get("/api/runs?offset=10").json()["runs"] == []
    assert c.get("/api/runs?offset=-1").status_code == 422
    assert c.get("/api/runs?limit=0").status_code == 422


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
    from tester.webapp.runner import build_command, tf_minutes

    base = {"pair": "BTC/USDT:USDT", "timerange": "20260801-20260901", "wallet": 10000, "fee": 0.0005}
    cmd = build_command("py", Path("p.json"), {**base, "timeframe": "15m", "timeframe_detail": "1m"})
    assert cmd[cmd.index("--timeframe") + 1] == "15m" and "--timeframe-detail" in cmd
    cmd = build_command("py", Path("p.json"), {**base, "timeframe": "1m", "timeframe_detail": "1m"})
    assert "--timeframe-detail" not in cmd  # detail musí byť jemnejší než TF grafu
    cmd = build_command("py", Path("p.json"), base)
    assert cmd[cmd.index("--timeframe") + 1] == "3m"
    assert tf_minutes("1h") == 60 and tf_minutes("3m") == 3


def test_submit_validates_timeframe(client, monkeypatch):
    import tester.webapp.app as app_mod

    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["1m", "3m", "5m"])
    # test je o kontrole timeframu, nie o tom, pre ktory engine su na disku data
    monkeypatch.setattr(app_mod.engines, "available", lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    c, _ = client
    base = {"params": IBSConfig().to_dict(), "pair": "BTC/USDT:USDT", "timerange": "20260801-20260901"}
    assert c.post("/api/runs", json={**base, "timeframe": "2m"}).status_code == 422
    assert c.post("/api/runs", json={**base, "timeframe": "15m"}).status_code == 422  # nie sú dáta
    job = c.post("/api/runs", json={**base, "timeframe": "5m"}).json()
    assert job["settings"]["timeframe"] == "5m" and job["settings"]["timeframe_detail"] == "1m"
    job = c.post("/api/runs", json={**base, "timeframe": "1m"}).json()
    assert job["settings"]["timeframe_detail"] is None
    assert c.post("/api/runs", json=base).json()["settings"]["timeframe"] == "3m"


def test_meta_carries_every_strategy_and_runs_default_to_ibs(client):
    c, store = client
    m = c.get("/api/meta").json()
    keys = [s["key"] for s in m["strategies"]]
    assert "ibs" in keys and set(m["strategy_meta"]) == set(keys)
    ibs = m["strategy_meta"]["ibs"]
    assert len(ibs["params"]) == len(m["params"]) and ibs["defaults"] == m["defaults"]
    assert any(l["id"] == "imb" and l["hollow_kinds"] == ["imb_box"] for l in m["strategies"][keys.index("ibs")]["layers"])

    # starý záznam bez settings.strategy sa číta ako ibs, nový beh nesie stratégiu
    store.save(_record("20260905-120000-aaaaaa"), trades=[], log="")
    lst = c.get("/api/runs", params={"q": "strat=ibs"}).json()
    assert lst["total"] == 1 and lst["runs"][0]["settings"]["strategy"] == "ibs"
    assert c.get("/api/runs/20260905-120000-aaaaaa").json()["record"]["settings"]["strategy"] == "ibs"
    base = {"params": IBSConfig().to_dict(), "pair": "BTC/USDT:USDT", "timerange": "20260801-20260901"}
    assert c.post("/api/runs", json={**base, "strategy": "neexistuje"}).status_code == 422
    job = c.post("/api/runs", json={**base, "strategy": "ibs"}).json()
    assert job["settings"]["strategy"] == "ibs"
    prof = c.get("/api/profiles/ibs/golden_binance_btcusdt_3m").json()
    assert prof["strategy"] == "ibs" and prof["params"]["legacyPineSizing"] is True
    assert c.get("/api/profiles/golden_binance_btcusdt_3m", params={"strategy": "neexistuje"}).status_code == 404


def test_submit_uses_tester_name_from_request(client, monkeypatch):
    """Meno z hlavičky stránky ide k behu; bez neho sa použije predvolené."""
    import tester.webapp.app as app_mod

    monkeypatch.setattr(app_mod, "current_user", lambda: "predvolene")
    # test je o mene testera, nie o tom, pre ktory engine su na disku data
    monkeypatch.setattr(app_mod.engines, "available", lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
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
    from tester.webapp.runner import check_market_rules

    params = IBSConfig().to_dict()
    check_market_rules("BTC/USDT:USDT", {**params, "tradeDirection": "Both", "leverage": 10})  # futures: v poriadku
    check_market_rules("BTC/USDT", {**params, "tradeDirection": "Long only", "leverage": 1})

    with pytest.raises(ValueError, match="shorty"):
        check_market_rules("BTC/USDT", {**params, "tradeDirection": "Both", "leverage": 1})
    with pytest.raises(ValueError, match="páka"):
        check_market_rules("ETH/USDT", {**params, "tradeDirection": "Long only", "leverage": 5})


def test_spot_pair_runs_with_spot_config_and_file_layout():
    from tester.webapp.chart import pair_file
    from tester.webapp.runner import build_command

    base = {"timerange": "20250101-20250201", "wallet": 10000, "fee": 0.0005, "timeframe": "3m"}
    spot = build_command("py", Path("p.json"), {**base, "pair": "BTC/USDT"})
    futures = build_command("py", Path("p.json"), {**base, "pair": "BTC/USDT:USDT"})
    assert spot[spot.index("--config") + 1].endswith("config.tester.spot.json")
    assert futures[futures.index("--config") + 1].endswith("config.tester.json")
    # beh ide cez obal, ktory najprv zaregistruje burzu Tester
    assert futures[:4] == [futures[0], "-m", "tester.ftrun", "backtesting"]

    assert pair_file("BTC/USDT", "3m").name == "BTC_USDT-3m.feather"
    assert pair_file("BTC/USDT:USDT", "3m").name == "BTC_USDT_USDT-3m-futures.feather"
    assert pair_file("BTC/USDT", "3m").parent.name == "spot"
    assert pair_file("BTC/USDT:USDT", "3m").parent.name == "futures"


def test_instrument_knows_its_market_and_exchange_name():
    from tradebot.core.types import INSTRUMENTS

    perp, spot = INSTRUMENTS["btcusdt_binance"], INSTRUMENTS["btcusdt_binance_spot"]
    assert (perp.exchange_symbol, perp.market, perp.is_spot) == ("BTCUSDT.P", "futures", False)
    assert (spot.exchange_symbol, spot.market, spot.is_spot) == ("BTCUSDT", "spot", True)


def test_submit_rejects_shorts_on_spot(client, monkeypatch):
    import tester.webapp.app as app_mod

    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["1m", "3m"])
    monkeypatch.setattr(app_mod.engines, "available", lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
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
    import tester.webapp.profiles as profiles_mod

    d = tmp_path / "profiles"
    monkeypatch.setattr(profiles_mod, "PROFILES_DIR", d)
    return d


def test_save_run_as_profile_writes_every_field(client, own_profiles):
    """Vlastný profil je úplný, nie diff — inak by ho posunula zmena Pine defaultu
    alebo profilu, z ktorého vznikol, a starý beh by sa nedal zopakovať."""
    c, store = client
    rec = _record("20260905-120000-aaaaaa", params={"rrRatio": 5.0})
    rec["settings"]["timeframe"] = "3m"
    store.save(rec)
    r = c.post("/api/profiles", json={"name": "moj_rr5", "from_run": "20260905-120000-aaaaaa",
                                      "note": "RR 5"})
    assert r.status_code == 200 and r.json()["user_profiles"] == ["moj_rr5"]

    data = json.loads((own_profiles / "moj_rr5.json").read_text(encoding="utf-8"))
    assert data["_instrument"] == "btcusdt_binance" and data["rrRatio"] == 5.0
    assert "RR 5" in data["_comment"] and "20260905-120000-aaaaaa" in data["_comment"]
    # každé pole configu, aj to, čo má práve hodnotu Pine defaultu
    assert {k for k in data if not k.startswith("_")} == set(IBSConfig().to_dict())
    assert data["enableImbEntry"] is True

    p = c.get("/api/profiles/moj_rr5").json()
    assert p["params"]["rrRatio"] == 5.0 and p["instrument"] == "btcusdt_binance" and p["kind"] == "user"
    meta = c.get("/api/meta").json()
    assert "moj_rr5" in meta["profiles"] and meta["user_profiles"] == ["moj_rr5"]
    # Profil vie, kedy vznikol, a stránka ho volá „dátum · pár TF · popis".
    assert data["_created"][:4] == "2026" or data["_created"][:2] == "20"
    info = meta["profile_info"]["moj_rr5"]
    assert info["created"] == data["_created"] and info["pair"] == "BTC/USDT:USDT"
    assert info["timeframe"] == "3m" and info["title"] == "RR 5"
    # Profil repozitára dátum nemá - čas súboru z gitu o vzniku nič nehovorí.
    assert meta["profile_info"]["golden_binance_btcusdt_3m"]["created"] == ""


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


def test_profile_remembers_what_it_started_from(client, own_profiles):
    """Vlastný profil si pamätá východiskový profil — inak sa po pár úpravách nedá
    povedať, či je to golden s RR 4, alebo niečo úplne iné."""
    c, store = client
    store.save(_record("20260905-120000-aaaaaa", params={"rrRatio": 5.0}))  # beh mal profil z configs
    c.post("/api/profiles", json={"name": "z_behu", "from_run": "20260905-120000-aaaaaa"})
    assert c.get("/api/profiles/z_behu").json()["base"] == "btcusdt_3m_binance_ny"

    c.post("/api/profiles", json={"name": "z_formulara", "params": IBSConfig().to_dict(),
                                  "instrument": "btcusdt_binance", "base": "z_behu"})
    data = json.loads((own_profiles / "z_formulara.json").read_text(encoding="utf-8"))
    assert data["_base"] == "z_behu"
    # beh z Pine defaultov nemá z čoho vychádzať
    rec = _record("20260905-130000-bbbbbb")
    rec["settings"]["profile"] = None
    store.save(rec)
    c.post("/api/profiles", json={"name": "bez_zakladu", "from_run": "20260905-130000-bbbbbb"})
    assert c.get("/api/profiles/bez_zakladu").json()["base"] is None


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
    from tradebot.core.config import ConfigError
    from tester.webapp import profiles

    params = IBSConfig().to_dict()
    with pytest.raises(ConfigError):
        profiles.save("zly", {**params, "rrRatio": 99}, "btcusdt_binance")
    with pytest.raises(profiles.ProfileError):
        profiles.save("zly", params, "neznamy_nastroj")
    assert profiles.user_names() == []


def test_git_target_is_main_not_the_current_branch(monkeypatch):
    """História behov patrí do `main`. Keď webapp bežala z vývojárskeho worktree,
    push šiel na vetvu `claude/...` a v `main` po ňom nebolo ani stopy."""
    from tester.webapp import gitsync

    monkeypatch.delenv("IBS_GIT_BRANCH", raising=False)
    assert gitsync.target() == "main"
    monkeypatch.setenv("IBS_GIT_BRANCH", "test-vetva")
    assert gitsync.target() == "test-vetva"


def test_git_push_refuses_commits_outside_tester_data(monkeypatch):
    """Kód z testerského klonu do `main` nepatrí — Push to musí zastaviť."""
    from tester.webapp import gitsync

    calls = {}

    def fake_git(*args, check=False):
        calls["last"] = args
        out = ""
        if args[0] == "rev-list":
            out = "aaaaaaa1 bbbbbbb2"
        elif args[0] == "show":
            out = ("tradebot/core/engine.py" if args[-1] == "aaaaaaa1"
                   else "tester/runs/x/run.json")
        return type("P", (), {"args": ("git", *args), "stdout": out, "stderr": "", "returncode": 0})()

    monkeypatch.setattr(gitsync, "_git", fake_git)
    monkeypatch.setattr(gitsync, "_paths", lambda: ["tester/runs", "tester/profiles"])
    assert gitsync._foreign_commits("main") == ["aaaaaaa"]  # len ten commit s kódom


def test_git_recognizes_missing_github_login():
    """Webapp beží bez terminálu — git sa nemá koho spýtať na heslo. Musí to povedať
    ako návod, nie ako „fatal: could not read Username… Device not configured"."""
    from tester.webapp import gitsync

    assert gitsync._auth_failed("fatal: could not read Username for 'https://github.com': "
                                "Device not configured")
    assert gitsync._auth_failed("remote: Invalid username or token. Authentication failed")
    assert not gitsync._auth_failed("Everything up-to-date")
    assert "gh auth login" in gitsync.AUTH_HELP


def test_git_commit_message_counts_runs_and_profiles():
    from tester.webapp.gitsync import _message

    assert _message([" M tester/runs/a/run.json"]) == "Pridaj 1 beh backtestu z webapp"
    assert _message(["?? tester/profiles/moj.json"]) == "Pridaj 1 profil z webapp"
    mixed = _message([" M tester/runs/a/run.json",
                      "?? tester/runs/b/run.json",
                      "?? tester/profiles/moj.json"])
    assert mixed == "Pridaj 2 behy backtestu a 1 profil z webapp"


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #


def test_cli_parse_set_values():
    from tester.webapp.cli import parse_set

    assert parse_set("rrRatio=5") == ("rrRatio", 5)
    assert parse_set("useStructureFilter=true") == ("useStructureFilter", True)
    assert parse_set("minSlDistance=0.2@pct") == ("minSlDistance", {"value": 0.2, "unit": "pct"})
    assert parse_set("sess2TZ=America/New_York") == ("sess2TZ", "America/New_York")
    assert parse_set('minSlDistance={"value": 1, "unit": "atr"}') == ("minSlDistance", {"value": 1, "unit": "atr"})
    assert parse_set("tickDollarValue=null") == ("tickDollarValue", None)
    with pytest.raises(SystemExit):
        parse_set("bez_rovnasa")


def test_cli_list_and_show_read_the_store(tmp_path: Path, monkeypatch, capsys):
    import tester.webapp.cli as cli
    import tester.webapp.store as store_mod

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


def test_cli_sweeps_najde_mriezku_v_historii(tmp_path: Path, monkeypatch, capsys):
    """Mriežka spustená vo webapp sa musí dať otvoriť aj z terminálu — je to tá istá história."""
    import tester.webapp.cli as cli
    import tester.webapp.store as store_mod

    store = RunStore(tmp_path)
    for i, (rr, be) in enumerate([(2, 0.10), (5, 0.30)]):
        rec = _record(f"2026090{i + 1}-120000-bbbb0{i}", params={"rrRatio": float(rr)})
        rec["settings"]["sweep"] = {"id": "20260901-120000-abcd", "values": {"rrRatio": rr},
                                    "goal": "break_even", "max_dd": None, "min_trades": None}
        rec["result"] = {**rec["result"], "break_even_pct": be}
        store.save(rec)
    monkeypatch.setattr(store_mod, "RUNS_DIR", tmp_path)

    assert cli.main(["sweeps"]) == 0
    out = capsys.readouterr().out
    assert "20260901-120000-abcd" in out and "rrRatio" in out

    assert cli.main(["sweeps", "20260901-120000-abcd"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("=== sweep 20260901-120000-abcd")
    assert "<- najlepsi" in out                      # najvyšší break-even je rrRatio 5
    assert out.index("0.3000") < out.index("0.1000")

    with pytest.raises(SystemExit):
        cli.main(["sweeps", "20990101-000000-zzzz"])


def test_user_profile_belongs_to_its_strategy(client, own_profiles):
    """Vlastný profil nesie `_strategy`; ponuka inej stratégie ho neukáže a načíta sa jej configom."""
    from tradebot.strategies.demo_breakout.config import DemoBreakoutConfig

    c, _ = client
    body = {"name": "demo_moj", "strategy": "demo_breakout", "instrument": "btcusdt_binance",
            "params": {**DemoBreakoutConfig().to_dict(), "channelLen": 33}, "timeframe": "5m"}
    r = c.post("/api/profiles", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["strategy"] == "demo_breakout" and r.json()["user_profiles"] == ["demo_moj"]
    data = json.loads((own_profiles / "demo_moj.json").read_text(encoding="utf-8"))
    assert data["_strategy"] == "demo_breakout" and data["channelLen"] == 33
    assert set(k for k in data if not k.startswith("_")) == set(DemoBreakoutConfig().to_dict())

    assert c.get("/api/profiles", params={"strategy": "ibs"}).json()["user_profiles"] == []
    assert "demo_moj" in c.get("/api/profiles", params={"strategy": "demo_breakout"}).json()["profiles"]
    meta = c.get("/api/meta").json()
    assert "demo_moj" not in meta["profiles"]
    assert "demo_moj" in meta["strategy_meta"]["demo_breakout"]["profiles"]

    got = c.get("/api/profiles/demo_moj", params={"strategy": "demo_breakout"}).json()
    assert got["params"]["channelLen"] == 33 and got["kind"] == "user" and got["timeframe"] == "5m"
    assert c.get("/api/profiles/demo_moj", params={"strategy": "ibs"}).status_code == 404
    # IBS parametre pod demo stratégiou config odmietne
    assert c.post("/api/profiles", json={**body, "name": "zle", "params": IBSConfig().to_dict()}).status_code == 422


# --------------------------------------------------------------------------- #
# Monte Carlo v detaile behu
# --------------------------------------------------------------------------- #


MC_TRADES = [{"open_rate": 100.0, "close_rate": 110.0, "amount": 1.0, "is_short": False}] * 4 + [
    {"open_rate": 100.0, "close_rate": 90.0, "amount": 1.0, "is_short": False}]


def test_montecarlo_endpoint_vrati_interval_a_histogram(client):
    c, store = client
    store.save(_record("20260905-120000-abc123"), trades=MC_TRADES)
    r = c.get("/api/runs/20260905-120000-abc123/montecarlo", params={"iterations": 500}).json()
    assert r["n"] == 5 and r["iterations"] == 500 and r["run_id"] == "20260905-120000-abc123"
    assert r["fee_pct"] == pytest.approx(0.05)          # 0,0005 zo settings behu
    be = r["break_even"]
    assert be["lo"] < be["observed"] < be["hi"]
    assert len(be["hist"]["centers"]) == len(be["hist"]["counts"]) == 40
    assert sum(be["hist"]["counts"]) == 500
    assert r["n"] < r["min_trades"]                     # webapp na malú vzorku upozorní
    assert r["block"] == 1                              # z piatich obchodov sa dlhší blok nelosuje


def test_montecarlo_endpoint_berie_poplatok_z_dopytu(client):
    c, store = client
    store.save(_record("20260905-120000-abc123"), trades=MC_TRADES)
    url = "/api/runs/20260905-120000-abc123/montecarlo"
    lacne = c.get(url, params={"fee": 0.0, "iterations": 500}).json()
    drahe = c.get(url, params={"fee": 1.0, "iterations": 500}).json()
    assert lacne["net"]["observed"] > drahe["net"]["observed"]
    assert lacne["break_even"]["p_above_fee"] > drahe["break_even"]["p_above_fee"]
    # break-even samotný od sadzby nezávisí, počíta sa z cien
    assert lacne["break_even"]["observed"] == pytest.approx(drahe["break_even"]["observed"])


def test_montecarlo_endpoint_pocita_ucet_z_penazenky_a_profilu(client):
    c, store = client
    rec = _record("20260905-120000-abc123")           # wallet 10 000, maxLossDollar z Pine defaultu
    rec["params"]["maxLossDollar"] = 100.0
    rec["params"]["legacyPineSizing"] = False
    store.save(rec, trades=MC_TRADES)
    url = "/api/runs/20260905-120000-abc123/montecarlo"
    acc = c.get(url, params={"iterations": 500}).json()["account"]
    assert acc["start"] == 10_000.0 and acc["risk"] == 100.0 and acc["scalable"] is True
    assert [h["limit"] for h in acc["hits"]] == [10.0, 20.0, 30.0, 50.0]
    assert acc["advice"]["limit"] == 20.0

    vacsie = c.get(url, params={"iterations": 500, "risk": 300}).json()["account"]
    assert vacsie["risk"] == 300.0
    assert vacsie["drawdown_abs"]["median"] > acc["drawdown_abs"]["median"]
    # odporúčané riziko je vlastnosť stratégie a účtu, nie práve zvoleného rizika
    assert vacsie["advice"]["risk"] == pytest.approx(acc["advice"]["risk"], rel=1e-6)

    # malý účet a väčšie riziko: jedna strata je 15 % účtu, takže hranice začnú padať
    maly = c.get(url, params={"iterations": 500, "account": 1000, "risk": 1500}).json()["account"]
    assert maly["start"] == 1000.0
    assert maly["hits"][0]["p"] > acc["hits"][0]["p"] == 0.0


def test_montecarlo_endpoint_hlasi_chybajuci_beh_aj_beh_bez_obchodov(client):
    c, store = client
    store.save(_record("20260905-120000-abc123"), trades=[])
    assert c.get("/api/runs/20260905-999999-zzzzzz/montecarlo").status_code == 404
    assert c.get("/api/runs/20260905-120000-abc123/montecarlo").status_code == 422


def test_montecarlo_sa_pamata_a_neprepocitava(client):
    from tester.webapp import app as app_mod

    c, store = client
    store.save(_record("20260905-120000-abc123"), trades=MC_TRADES)
    url = "/api/runs/20260905-120000-abc123/montecarlo"
    app_mod._MC_CACHE.clear()
    prvy = c.get(url, params={"iterations": 500}).json()
    assert len(app_mod._MC_CACHE) == 1
    assert c.get(url, params={"iterations": 500}).json() == prvy
    assert len(app_mod._MC_CACHE) == 1
    c.get(url, params={"iterations": 500, "fee": 0.2})       # iná sadzba je iný záznam
    assert len(app_mod._MC_CACHE) == 2


def _stub_launcher(monkeypatch, chyba: list):
    """`python -m tester.webapp` bez uvicornu a bez skladania dát; vráti zoznam volaní."""
    import sys
    import types

    monkeypatch.setitem(sys.modules, "uvicorn", types.SimpleNamespace(run=lambda *a, **k: None))
    merges: list[list[str]] = []
    monkeypatch.setattr("tester.data_archive.missing", lambda: chyba)
    monkeypatch.setattr("tester.data_archive.main", lambda argv: merges.append(argv) or 0)
    monkeypatch.setattr("tester.timeframes.missing", lambda: [])
    monkeypatch.setattr("tester.timeframes.ensure", lambda: [])
    return merges


def test_spustac_webapp_sklada_data_ked_nejake_chybaju(monkeypatch, capsys):
    """`python -m tester.webapp` pred štartom doplní, čo z archívu chýba.

    Dve regresie naraz: spúšťač najprv ukazoval na `runner.DATA_DIR`, ktorý po presune
    dát neexistoval (padol na ImportError), a potom sa pýtal len „je v data/ aspoň jeden
    feather" — čo pri jedinom rozbalenom zdroji prešlo a backtest spadol až na chýbajúcu
    históriu páru.
    """
    from pathlib import Path

    from tester.webapp import __main__ as entry

    merges = _stub_launcher(monkeypatch, [Path("data/tester/binance/futures/BTC-3m.feather")])
    assert entry.main() == 0
    out = capsys.readouterr().out
    assert merges == [["merge"]]
    assert "Chyba 1 pracovnych suborov" in out
    assert "TradeBot Tester: http://" in out


def test_spustac_webapp_nesklada_ked_je_vsetko_rozbalene(monkeypatch, capsys):
    from tester.webapp import __main__ as entry

    merges = _stub_launcher(monkeypatch, [])
    assert entry.main() == 0
    assert merges == []
    assert "TradeBot Tester: http://" in capsys.readouterr().out


def test_spustac_webapp_doplni_chybajuce_timeframy(monkeypatch, capsys):
    """Vyšší TF si Freqtrade z 1m nedopočíta — musí byť na disku pred prvým behom."""
    from pathlib import Path

    from tester.webapp import __main__ as entry

    _stub_launcher(monkeypatch, [])
    volania: list[str] = []
    monkeypatch.setattr("tester.timeframes.missing",
                        lambda: [Path("data/tester/binance/spot/BTC_USDT-4h.feather")])
    monkeypatch.setattr("tester.timeframes.ensure", lambda: volania.append("ensure") or [])
    assert entry.main() == 0
    assert volania == ["ensure"]
    assert "Chyba 1 timeframov" in capsys.readouterr().out


def test_ponuka_parov_nesie_zdroj_trh_aj_druh(client, monkeypatch):
    """Z jedného riadku ponuky má byť vidno, odkiaľ sviečky sú a aký je to trh."""
    c, _ = client
    pairs = c.get("/api/meta").json()["pairs"]
    if not pairs:
        pytest.skip("bez dát nie je čo ponúkať")
    for p in pairs:
        assert p["source"] and p["market"] in ("spot", "futures")
        assert p["kind"] in ("spot", "futures", "cfd")
        assert p["exchanges"] == [] or p["exchanges"][0] in ("tester", p["source"], "dukascopy")


def test_staticke_subory_sa_necachuju(client):
    """Po aktualizácii nesmie prehliadač podať starú stránku — tester by nové pole nevidel."""
    c, _ = client
    r = c.get("/static/app.js")
    assert r.status_code == 200
    assert "no-cache" in r.headers.get("cache-control", "")


def test_formular_ma_vsetky_ovladace_ktore_stranka_pouziva():
    """Redizajn formulára nesmie zahodiť žiadne pole — JS ich hľadá podľa `id`."""
    from tester.webapp.app import STATIC

    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for name in ("strategy", "profile", "profile-save", "profile-rename", "profile-delete",
                 "profile-msg", "profile-base", "pair", "pair-market", "pair-range",
                 "engine", "engine-note", "exchange", "exchange-note", "tf", "from", "to",
                 "fee", "wallet", "detail", "note", "run", "run-error",
                 "pair-warn", "trading-warn"):
        assert f'id="{name}"' in html, name


def test_stranka_sa_necachuje(client):
    """Keby cachovala index.html, odkaz na nový skript by sa k prehliadaču nedostal."""
    c, _ = client
    r = c.get("/")
    assert r.status_code == 200 and "no-cache" in r.headers.get("cache-control", "")


def test_odkazy_na_skript_a_styly_maju_verziu(client):
    """`no-cache` nestačí na kópiu, ktorú si prehliadač uložil ešte pred jej pridaním.

    Chrome takú považuje za čerstvú podľa vlastnej heuristiky a znova sa nepýta (Edge áno),
    takže stránka bola nová a štýly staré. Verzia v URL je iný kľúč cache.
    """
    import re

    c, _ = client
    html = c.get("/").text
    assert re.search(r'href="/static/app\.css\?v=[0-9a-f]+"', html)
    assert re.search(r'src="/static/app\.js\?v=[0-9a-f]+"', html)
    # verzia sa mení len so súborom, nie s každým načítaním
    assert c.get("/").text == html


# --------------------------------------------------------------------------- #
# sweep: mriežka behov
# --------------------------------------------------------------------------- #


def _sweep_body(**over):
    body = {"params": IBSConfig().to_dict(), "pair": "BTC/USDT:USDT",
            "timerange": "20250904-20260904", "space": {"rrRatio": "2:4:1"},
            "goal": "break_even", "note": "test"}
    body.update(over)
    return body


def test_sweep_zaradi_kazdy_bod_ako_samostatny_beh(client, monkeypatch):
    from tester.webapp import app as app_mod

    c, store = client
    monkeypatch.setattr(app_mod.engines, "available",
                        lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])
    # fronta stojí: falošný beh skončí za ~50 ms a prvý bod by z fronty stihol zmiznúť
    monkeypatch.setattr(c.app.state.runner, "start", lambda: None)

    r = c.post("/api/sweeps", json=_sweep_body())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["points"] == 3 and len(body["runs"]) == 3
    assert body["goal_note"] == "najvyšší break-even poplatok"

    # každý beh nesie svoju hodnotu aj spoločnú značku
    jobs = c.get("/api/queue").json()
    hodnoty = sorted(j["settings"]["sweep"]["values"]["rrRatio"] for j in jobs)
    assert hodnoty == [2, 3, 4]
    assert {j["settings"]["sweep"]["id"] for j in jobs} == {body["id"]}


def test_sweep_odmietne_nezmyselne_zadanie(client, monkeypatch):
    from tester.webapp import app as app_mod

    c, _ = client
    monkeypatch.setattr(app_mod.engines, "available",
                        lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])

    assert c.post("/api/sweeps", json=_sweep_body(space={"nieco": "1,2"})).status_code == 422
    assert c.post("/api/sweeps", json=_sweep_body(space={})).status_code == 422
    assert c.post("/api/sweeps", json=_sweep_body(goal="nieco")).status_code == 422
    assert c.post("/api/sweeps", json=_sweep_body(space={"rrRatio": "2:6"})).status_code == 422


def test_sweep_s_hodnotou_mimo_rozsahu_nezaradi_nic(client, monkeypatch):
    """Regresia: bod mimo Pine rozsahu padal až v `submit` a stránka dostala 500.

    Mriežka sa preto overí celá ešte pred zaradením — inak by pri chybe v piatom bode
    ostali vo fronte štyri behy a tester by k tomu dostal hlášku, ktorá nesúvisí.
    """
    from tester.webapp import app as app_mod

    c, _ = client
    monkeypatch.setattr(app_mod.engines, "available",
                        lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])

    r = c.post("/api/sweeps", json=_sweep_body(space={"rrRatio": "0:3:1"}))
    assert r.status_code == 422
    assert "rrRatio=0" in r.json()["detail"] and "mimo rozsahu" in r.json()["detail"]
    assert c.get("/api/queue").json() == []


def test_strop_mriezky_sa_da_zdvihnut(tmp_path, monkeypatch):
    """Strop je poistka proti preklepu v kroku, nie výkonový limit — preto sa dá posunúť."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.webapp import app as app_mod
    from tester.webapp.runner import BacktestRunner

    monkeypatch.setattr(app_mod.engines, "available",
                        lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])

    def app_with_cap(cap: str):
        monkeypatch.setenv("TRADEBOT_MAX_SWEEP_RUNS", cap)
        runner = BacktestRunner(RunStore(tmp_path / cap),
                                command_builder=lambda *a: ["python", "-c", "raise SystemExit(0)"])
        return TestClient(app_mod.create_app(RunStore(tmp_path / cap), runner))

    tesna = app_with_cap("4")
    r = tesna.post("/api/sweeps", json=_sweep_body(space={"rrRatio": "2:10:1"}))   # 9 bodov
    assert r.status_code == 422 and "strop je 4" in r.json()["detail"]
    assert tesna.get("/api/meta").json()["max_sweep_runs"] == 4

    siroka = app_with_cap("50")
    assert siroka.post("/api/sweeps", json=_sweep_body(space={"rrRatio": "2:10:1"})).status_code == 200


def test_sweep_hlasi_odhad_casu_a_ma_vlastnu_znacku(client, monkeypatch):
    """Rok backtestu je ~30 s, takže mriežka je otázka času, nie počtu riadkov."""
    from tester.webapp import app as app_mod

    c, _ = client
    monkeypatch.setattr(app_mod.engines, "available",
                        lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])

    prvy = c.post("/api/sweeps", json=_sweep_body()).json()
    druhy = c.post("/api/sweeps", json=_sweep_body(space={"rrRatio": "5,6"})).json()

    assert prvy["minutes"] == 2                      # 3 body x rok x 30 s
    # Dva sweepy v tej istej sekunde sa nesmú zliať do jednej mriežky.
    assert prvy["id"] != druhy["id"]


def test_tu_istu_mriezku_druhy_raz_nezaradime(client, monkeypatch):
    """Kým mriežka čaká vo fronte, v tabuľke sa nič nedeje — a tester klikne znova.

    Štyri rovnaké mriežky za sebou znamenajú štvornásobok času a ani jeden nový výsledok.
    """
    from tester.webapp import app as app_mod

    c, _ = client
    monkeypatch.setattr(app_mod.engines, "available",
                        lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])
    # Testujeme cakajucu frontu; rychly podproces nesmie nahodou dobehnut pred GET.
    monkeypatch.setattr(c.app.state.runner, "start", lambda: None)

    assert c.post("/api/sweeps", json=_sweep_body()).status_code == 200
    znova = c.post("/api/sweeps", json=_sweep_body())
    assert znova.status_code == 409 and "už čaká vo fronte" in znova.json()["detail"]
    assert len(c.get("/api/queue").json()) == 3      # nič nepribudlo


def test_sweep_vidno_od_zaradenia_aj_ked_este_nic_nedobehlo(client, monkeypatch):
    """Regresia: detail vracal len hotové behy, takže hneď po zaradení bola tabuľka
    prázdna a stav hlásil „hotových 0" — vyzeralo to, že sa nič nedeje."""
    from tester.webapp import app as app_mod

    c, _ = client
    # Testujeme čakajúcu frontu; rýchly podproces nesmie náhodou dobehnúť pred GET.
    monkeypatch.setattr(c.app.state.runner, "start", lambda: None)
    monkeypatch.setattr(app_mod.engines, "available",
                        lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])

    sweep_id = c.post("/api/sweeps", json=_sweep_body()).json()["id"]
    body = c.get(f"/api/sweeps/{sweep_id}").json()

    assert body["done"] == 0 and body["running"] == 3
    assert len(body["rows"]) == 3
    assert {row["status"] for row in body["rows"]} <= {"queued", "running"}
    assert sorted(row["values"]["rrRatio"] for row in body["rows"]) == [2, 3, 4]


def test_cela_mriezka_sa_da_zrusit_naraz(tmp_path, monkeypatch):
    """Mriežka nemá strop, tak musí ísť zrušiť — inak by preklep v kroku zapchal frontu.

    Zrušenie je náhrada za obmedzenie: sweep smie bežať aj celú noc, ale omyl sa opraví
    jedným klikom, nie ✕ pri každom bode.
    """
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.webapp import app as app_mod
    from tester.webapp.runner import BacktestRunner

    monkeypatch.setattr(app_mod.engines, "available",
                        lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])

    runner = BacktestRunner(RunStore(tmp_path), command_builder=lambda *a: ["python", "-c", ""])
    monkeypatch.setattr(runner, "start", lambda: None)   # fronta stojí, nech sa dá rušiť
    c = TestClient(app_mod.create_app(RunStore(tmp_path), runner))

    sweep_id = c.post("/api/sweeps", json=_sweep_body()).json()["id"]
    iny = c.post("/api/sweeps", json=_sweep_body(space={"rrRatio": "5,6"})).json()["id"]

    r = c.post(f"/api/sweeps/{sweep_id}/cancel")
    assert r.status_code == 200 and r.json()["cancelled"] == 3
    # Cudzia mriežka ostáva nedotknutá.
    assert c.get(f"/api/sweeps/{iny}").json()["running"] == 2
    assert c.post(f"/api/sweeps/{sweep_id}/cancel").status_code == 404


def test_mriezka_nema_strop_kym_ho_nikto_nezapne(client, monkeypatch):
    """Sweep sa púšťa cez noc alebo na serveri; vymyslené číslo by len prekážalo."""
    from tester.webapp import app as app_mod

    c, _ = client
    monkeypatch.setattr(app_mod.engines, "available",
                        lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])

    assert c.get("/api/meta").json()["max_sweep_runs"] == 0
    r = c.post("/api/sweeps", json=_sweep_body(space={"rrRatio": "0.5:10:0.05"}))
    assert r.status_code == 200 and r.json()["points"] == 191


def test_zoznam_mriezok_sa_posklada_z_historie(client, monkeypatch):
    """Mriežky sa neukladajú zvlášť — značka je v každom behu, zoznam je preskupená história.

    Vďaka tomu prežije reštart appky aj `git pull` cudzích behov a nedá sa rozísť s tým,
    čo je naozaj odbehnuté.
    """
    from tester.webapp import app as app_mod

    c, store = client
    monkeypatch.setattr(app_mod.engines, "available",
                        lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])
    # Testujeme cakajucu frontu; rychly podproces nesmie nahodou dobehnut pred GET.
    monkeypatch.setattr(c.app.state.runner, "start", lambda: None)

    for i, rr in enumerate([2, 3]):
        rec = _record(f"2026090{i + 1}-120000-aaaa0{i}")
        rec["settings"]["sweep"] = {"id": "20260901-120000-abcd", "values": {"rrRatio": rr},
                                    "goal": "winrate", "max_dd": 15.0, "min_trades": None}
        store.save(rec)
    bezi = c.post("/api/sweeps", json=_sweep_body()).json()["id"]

    body = c.get("/api/sweeps").json()
    podla_id = {s["id"]: s for s in body["sweeps"]}

    assert body["total"] == 2
    assert body["sweeps"][0]["id"] == bezi           # najnovšia hore
    stara = podla_id["20260901-120000-abcd"]
    assert stara["done"] == 2 and stara["pending"] == 0
    assert stara["params"] == ["rrRatio"] and stara["goal"] == "winrate"
    assert "drawdown" in stara["goal_note"]
    # Mriežka, ktorá ešte beží, je v zozname tiež — inak by z nej cez noc nebolo vidieť nič.
    assert podla_id[bezi]["pending"] == 3 and podla_id[bezi]["done"] == 0


def test_historia_mriezok_patri_strategii(client, monkeypatch):
    """Parametre sú v každej stratégii iné, takže mriežka cez `rrRatio` nemá pri Donchian
    breakoute čo robiť — zoznam sa prepína spolu s formulárom."""
    from tester.webapp import app as app_mod

    c, store = client
    monkeypatch.setattr(app_mod.engines, "available",
                        lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])
    # Testujeme cakajucu frontu; rychly podproces nesmie nahodou dobehnut pred GET.
    monkeypatch.setattr(c.app.state.runner, "start", lambda: None)

    for i, (strategia, znacka) in enumerate([("ibs", "20260901-120000-aaaa"),
                                             ("demo_breakout", "20260902-120000-bbbb")]):
        rec = _record(f"2026090{i + 1}-120000-cccc0{i}")
        rec["settings"]["strategy"] = strategia
        rec["settings"]["sweep"] = {"id": znacka, "values": {"rrRatio": 3},
                                    "goal": "break_even", "max_dd": None, "min_trades": None}
        store.save(rec)

    vsetky = c.get("/api/sweeps").json()
    assert {s["id"] for s in vsetky["sweeps"]} == {"20260901-120000-aaaa", "20260902-120000-bbbb"}

    len_ibs = c.get("/api/sweeps", params={"strategy": "ibs"}).json()
    assert [s["id"] for s in len_ibs["sweeps"]] == ["20260901-120000-aaaa"]
    assert len_ibs["sweeps"][0]["strategy"] == "ibs"

    len_demo = c.get("/api/sweeps", params={"strategy": "demo_breakout"}).json()
    assert [s["id"] for s in len_demo["sweeps"]] == ["20260902-120000-bbbb"]

    assert c.get("/api/sweeps", params={"strategy": "nieco"}).status_code == 404


def test_sweep_detail_zoradi_podla_kriteria(client):
    c, store = client
    for i, (rr, be, dd) in enumerate([(2, 0.10, 4.0), (3, 0.30, 30.0), (4, 0.20, 5.0)]):
        rec = _record(f"2026090{i+1}-120000-abc12{i}")
        rec["settings"]["sweep"] = {"id": "s1", "values": {"rrRatio": rr},
                                    "goal": "break_even", "max_dd": 10.0, "min_trades": None}
        rec["result"] = {**rec["result"], "break_even_pct": be, "max_drawdown_pct": dd, "trades": 40}
        store.save(rec)

    body = c.get("/api/sweeps/s1").json()
    assert body["params"] == ["rrRatio"] and body["done"] == 3
    assert [row["values"]["rrRatio"] for row in body["rows"]] == [4, 2, 3]
    assert body["rows"][-1]["why"] == "drawdown 30.0 % > 10 %"
    assert c.get("/api/sweeps/neznamy").status_code == 404


def test_analytics_configs_zoskupi_behy_s_rovnakymi_parametrami(tmp_path: Path):
    """Analytika sa počíta nad jednou konfiguráciou; ponuka konfigurácií hovorí, koľko
    okien a trhov ktorá pokrýva — bez toho by tester zlieval rôzne stratégie."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.webapp import app as app_mod

    store = RunStore(tmp_path)
    store.save(_record("20260905-120000-aaaaaa"))
    ine_okno = _record("20260906-120000-bbbbbb")
    ine_okno["settings"] = {**ine_okno["settings"], "timerange": "20240904-20250904"}
    store.save(ine_okno)
    store.save(_record("20260907-120000-cccccc", params={"rrRatio": 5.0}))
    c = TestClient(app_mod.create_app(store))

    out = c.get("/api/analytics/configs?strategy=ibs").json()["settings"]

    # Nastavenia sa volajú dátumom vzniku (najstarší beh) a v tom poradí aj idú:
    # rrRatio=5 vzniklo 7. 9., pôvodné 5. 9.
    assert [g["runs"] for g in out] == [1, 2]
    assert [g["first"] for g in out] == ["20260907-120000-cccccc", "20260905-120000-aaaaaa"]
    povodne = out[1]
    assert povodne["timeranges"] == ["20240904-20250904", "20250904-20260904"]
    assert povodne["profile"] == "btcusdt_3m_binance_ny" and povodne["trades"] == 298
    trh = povodne["markets"][0]
    assert trh["pair"] == "BTC/USDT:USDT" and trh["run_ids"] == ["20260905-120000-aaaaaa", "20260906-120000-bbbbbb"]
    # edge = break-even mínus poplatok behu: 0,141 - 0,05 > 0 v oboch oknách
    assert trh["positive"] == 2 and trh["done_ref"] == 2
    assert set(trh["windows"]) == {"20240904-20250904", "20250904-20260904"}
    # Ten istý profil, iné rrRatio: názov nesie parameter, v ktorom sa nastavenia líšia.
    assert list(povodne["variant"]) == ["rrRatio"] and out[0]["variant"]["rrRatio"] == 5.0


def test_doplnenie_okien_zaradi_len_chybajuce_referencne_okna(tmp_path: Path, monkeypatch):
    """Konfigurácia s jedným rokom: doplnia sa štyri ostatné referenčné okná s tými istými
    parametrami; konfigurácia so všetkými piatimi nedostane nič."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.hyperopt import REFERENCE_WINDOWS
    from tester.webapp import app as app_mod
    from tester.webapp.runner import BacktestRunner

    monkeypatch.setattr(app_mod.engines, "available",
                        lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])
    store = RunStore(tmp_path)
    store.save(_record("20260905-120000-aaaaaa", params={"rrRatio": 5.0}))
    runner = BacktestRunner(store, command_builder=lambda *a: ["python", "-c", "raise SystemExit(0)"])
    c = TestClient(app_mod.create_app(store, runner))

    konfig = c.get("/api/analytics/configs?strategy=ibs").json()["settings"][0]["markets"][0]
    assert konfig["missing"] == [w for w in REFERENCE_WINDOWS if w != "20250904-20260904"]

    out = c.post("/api/analytics/fill-windows", json={"run_id": konfig["sample"]}).json()
    assert out["windows"] == konfig["missing"] and len(out["queued"]) == 4
    # Falošný runner behy hneď dokončí: počká sa, kým fronta dobehne, a záznamy sa
    # čítajú zo skladu - medzi frontou a skladom je krátke okno, kde beh nie je nikde.
    import time as _time

    for _ in range(100):
        if not any(j.get("status") in ("queued", "running") for j in runner.snapshot()):
            break
        _time.sleep(0.05)
    for run_id in out["queued"]:
        for _ in range(100):
            j = store.get(run_id)
            if j is not None:
                break
            _time.sleep(0.05)
        assert j["settings"]["timerange"] in konfig["missing"]
        assert j["settings"]["checkup"]["fill"] == "20260905-120000-aaaaaa"
    assert c.post("/api/analytics/fill-windows", json={"run_id": "neexistuje"}).status_code == 404


def test_analytics_configs_nevidia_body_mriezky_ani_plato(tmp_path: Path):
    """Bod mriežky je iná stratégia na jednom okne, nie nastavenie, ktoré by niekto
    zvolil - v ponuke nastavení Analytiky nie je; doplnené okno a bunka matice áno."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.webapp import app as app_mod

    store = RunStore(tmp_path)
    store.save(_record("20260905-120000-aaaaaa"))
    bod = _record("20260906-120000-bbbbbb", params={"rrRatio": 5.0})
    bod["settings"] = {**bod["settings"], "sweep": {"id": "s1", "values": {"rrRatio": 5.0}}}
    store.save(bod)
    sused = _record("20260906-130000-cccccc", params={"rrRatio": 4.5})
    sused["settings"] = {**sused["settings"], "plateau": {"id": "p1", "param": "rrRatio"}}
    store.save(sused)
    doplnene = _record("20260907-120000-dddddd")
    doplnene["settings"] = {**doplnene["settings"], "timerange": "20240904-20250904",
                            "checkup": {"fill": "20260905-120000-aaaaaa", "strategy": "ibs"}}
    store.save(doplnene)
    c = TestClient(app_mod.create_app(store))

    out = c.get("/api/analytics/configs?strategy=ibs").json()["settings"]

    assert len(out) == 1 and out[0]["runs"] == 2
    assert out[0]["markets"][0]["run_ids"] == ["20260905-120000-aaaaaa", "20260907-120000-dddddd"]


def test_store_cache_vidi_novy_zmeneny_aj_zmazany_beh(tmp_path: Path):
    """Cache záznamov je len úspora čítania - pravda je disk: nový beh (aj z git pull),
    zmenený súbor a zmazaný adresár sa v ďalšom `all()`/`get()` prejavia."""
    import os
    import shutil
    import time as _time

    store = RunStore(tmp_path)
    store.save(_record("20260905-120000-aaaaaa"))
    assert [r["id"] for r in store.all()] == ["20260905-120000-aaaaaa"]

    # nový beh pribudol mimo store (git pull)
    (tmp_path / "20260906-120000-bbbbbb").mkdir()
    novy = _record("20260906-120000-bbbbbb")
    (tmp_path / "20260906-120000-bbbbbb" / "run.json").write_text(json.dumps(novy), encoding="utf-8")
    assert [r["id"] for r in store.all()] == ["20260906-120000-bbbbbb", "20260905-120000-aaaaaa"]

    # zmenený súbor (iný obsah aj mtime) - cache ho prečíta nanovo
    p = tmp_path / "20260905-120000-aaaaaa" / "run.json"
    zmeneny = {**_record("20260905-120000-aaaaaa"), "note": "prepisane"}
    _time.sleep(0.01)
    p.write_text(json.dumps(zmeneny), encoding="utf-8")
    os.utime(p, None)
    assert store.get("20260905-120000-aaaaaa")["note"] == "prepisane"

    # detail si do záznamu dopisuje polia - cache ostane čistá
    store.get("20260905-120000-aaaaaa")["has_chart"] = True
    assert "has_chart" not in store.get("20260905-120000-aaaaaa")

    # zmazaný adresár vypadne
    shutil.rmtree(tmp_path / "20260906-120000-bbbbbb")
    assert [r["id"] for r in store.all()] == ["20260905-120000-aaaaaa"]
    assert store.get("20260906-120000-bbbbbb") is None


def test_analytics_prepare_pouzije_hotove_behy_a_zaradi_len_chybajuce_okna(tmp_path: Path, monkeypatch):
    """Tester zadá profil, pár a TF: okno, ktoré má v histórii hotový beh s tými istými
    parametrami (aj keď beh uložil len prepísané kľúče), sa použije; zvyšné sa zaradia.
    `dry_run` nič nezaradí; body mriežky sa ako hotové neberú; beh vo fronte sa nezaradí
    druhýkrát."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.hyperopt import REFERENCE_WINDOWS
    from tester.webapp import app as app_mod
    from tester.webapp.runner import BacktestRunner

    monkeypatch.setattr(app_mod.engines, "available", lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.engines, "default_engine", lambda inst, tf="3m": "freqtrade")
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])
    monkeypatch.setattr(app_mod, "available_pairs", lambda: [{"pair": "BTC/USDT:USDT", "from": "2019-01-01", "to": "2026-09-10"}])
    store = RunStore(tmp_path)
    # Pine defaulty, uložené len ako prázdne parametre (starší beh) - stále tá istá konfigurácia.
    hotovy = _record("20260905-120000-aaaaaa", params={})
    hotovy["params"] = {}
    hotovy["settings"] = {**hotovy["settings"], "timeframe": "3m", "engine": "freqtrade", "profile": None}
    store.save(hotovy)
    # iné parametre v inom okne - nepatrí sem
    iny = _record("20260906-120000-bbbbbb", params={"rrRatio": 5.0})
    iny["settings"] = {**iny["settings"], "timeframe": "3m", "engine": "freqtrade", "timerange": "20240904-20250904"}
    store.save(iny)
    # bod mriežky s defaultmi v ďalšom okne - skúška parametra, nie hotový beh
    bod = _record("20260907-120000-cccccc")
    bod["settings"] = {**bod["settings"], "timeframe": "3m", "engine": "freqtrade", "timerange": "20231001-20241001",
                       "sweep": {"id": "s1", "values": {}}}
    store.save(bod)
    runner = BacktestRunner(store, command_builder=lambda *a: ["python", "-c", "raise SystemExit(0)"])
    monkeypatch.setattr(runner, "start", lambda: None)   # behy ostanú vo fronte, nič sa nespustí
    c = TestClient(app_mod.create_app(store, runner))
    body = {"strategy": "ibs", "profile": "", "pair": "BTC/USDT:USDT", "timeframe": "3m"}

    dry = c.post("/api/analytics/prepare", json={**body, "dry_run": True}).json()
    assert dry["ready"] == ["20260905-120000-aaaaaa"] and dry["queued"] == [] and dry["pending"] == []
    assert dry["missing"] == [w for w in REFERENCE_WINDOWS if w != "20250904-20260904"]
    assert dry["market"] == "BTC/USDT:USDT|3m" and dry["engine"] == "freqtrade"
    stav = {w["window"]: w["status"] for w in dry["windows"]}
    assert stav["20250904-20260904"] == "done" and stav["20231001-20241001"] == "missing"

    # okno mimo dát páru sa nedá dopočítať (kontroluje sa pred zaradením)
    monkeypatch.setattr(app_mod, "available_pairs", lambda: [{"pair": "BTC/USDT:USDT", "from": "2024-01-01", "to": "2026-09-10"}])
    mimo = c.post("/api/analytics/prepare", json={**body, "dry_run": True}).json()
    assert "20211001-20221001" in mimo["no_data"] and "20221001-20231001" in mimo["no_data"]
    monkeypatch.setattr(app_mod, "available_pairs", lambda: [{"pair": "BTC/USDT:USDT", "from": "2019-01-01", "to": "2026-09-10"}])

    out = c.post("/api/analytics/prepare", json=body).json()
    assert out["ready"] == ["20260905-120000-aaaaaa"] and len(out["queued"]) == 4
    assert set(out["queued"]) <= set(out["pending"])          # pending nesie aj syntetické dvojča
    for job_id in out["queued"]:
        j = runner.job(job_id)
        assert j.settings["timerange"] in dry["missing"] and j.settings["checkup"]["analytics"] == "(Pine defaulty)"
        assert j.settings["pair"] == "BTC/USDT:USDT" and j.params["rrRatio"] == IBSConfig().rrRatio
    # druhé Spočítať to isté nezaradí znova: čakajúce behy sa vrátia ako pending
    znova = c.post("/api/analytics/prepare", json=body).json()
    assert znova["queued"] == [] and set(znova["pending"]) >= set(out["queued"])

    assert c.post("/api/analytics/prepare", json={**body, "profile": "neexistuje"}).status_code == 404


def test_analytics_prepare_planuje_aj_synteticke_dvojca(tmp_path: Path, monkeypatch):
    """K analytike patrí to isté zadanie na premiešanom trhu: dvojča páru dostane svoje
    okná (hotový beh s tými istými parametrami sa použije, zvyšok sa zaradí) a čaká sa
    naň spolu s ostatnými. Pár bez dvojčaťa ho v `dry_run` len ohlási."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester import synthetic as syn_mod
    from tester.webapp import app as app_mod
    from tester.webapp.runner import BacktestRunner

    monkeypatch.setattr(app_mod.engines, "available", lambda inst, tf="3m", exchange=None: ["freqtrade", "multicharts"])
    monkeypatch.setattr(app_mod.engines, "default_engine", lambda inst, tf="3m": "freqtrade")
    monkeypatch.setattr(app_mod.chart_data, "available_timeframes", lambda pair: ["3m"])
    monkeypatch.setattr(app_mod, "available_pairs", lambda: [{"pair": "BTC/USDT:USDT", "from": "2019-01-01", "to": "2026-09-10"}])
    store = RunStore(tmp_path)
    synt = _record("20260905-120000-aaaaaa")
    synt["settings"] = {**synt["settings"], "pair": "SYNTH/USDT:USDT", "timeframe": "3m", "engine": "freqtrade"}
    store.save(synt)
    runner = BacktestRunner(store, command_builder=lambda *a: ["python", "-c", "raise SystemExit(0)"])
    monkeypatch.setattr(runner, "start", lambda: None)
    c = TestClient(app_mod.create_app(store, runner))
    body = {"strategy": "ibs", "profile": "", "pair": "BTC/USDT:USDT", "timeframe": "3m"}

    dry = c.post("/api/analytics/prepare", json={**body, "dry_run": True}).json()
    s = dry["synthetic"]
    assert s["pair"] == "SYNTH/USDT:USDT" and s["key"] == "synth"
    stav = {w["window"]: w["status"] for w in s["windows"]}
    assert stav["20250904-20260904"] == "done" and stav["20231001-20241001"] == "missing"
    # recept dvojčaťa siaha od 2021-10, staršie okno je bez dát
    assert stav["20211001-20221001"] in ("missing", "no_data")

    out = c.post("/api/analytics/prepare", json=body).json()
    assert len(out["queued"]) == 5                                  # skutočný pár: všetkých päť
    assert out["synthetic"]["ready"] == ["20260905-120000-aaaaaa"]
    assert out["synthetic"]["queued"] and set(out["synthetic"]["pending"]) <= set(out["pending"])
    for job_id in out["synthetic"]["queued"]:
        j = runner.job(job_id)
        assert j.settings["pair"] == "SYNTH/USDT:USDT" and "syntetický" in j.note

    # pár bez dvojčaťa: dry_run len povie, že vznikne pri Spočítať
    monkeypatch.setattr(syn_mod, "twin_for", lambda pair, registry=None: None)
    bez = c.post("/api/analytics/prepare", json={**body, "dry_run": True}).json()["synthetic"]
    assert bez["pair"] is None and "Spočítať" in bez["note"]
