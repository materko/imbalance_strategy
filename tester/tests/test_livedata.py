"""Živé dáta (`tester.livedata`, `tester.livesim`, docs/DATA.md „Živé dáta“): export zo zrkadla do `data_live`
oddelene od stiahnutých dát, 1m bary `m1`, behy z Testera von, obchody s profilom behu, poradie zdrojov
sviečok okolo hranice živého behu a párovanie skutočných a simulovaných obchodov."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tester import livedata, livesim
from tester.tests.test_dashboard_live import INST, MIN, T0, entry, fill, hello
from tradebot.live.schema import validate
from tradebot.live.store import LiveStore


def bar(seq: int, bt: int, px: float, kind: str = "bar") -> dict:
    ev = {"seq": seq, "t": bt + 3 * MIN, "k": kind, "bt": bt, "o": px, "h": px + 2, "l": px - 1, "c": px + 1, "v": 10.0}
    if kind == "bar":
        ev["ready"] = True
    return validate(ev)


def _mirror(path: Path) -> None:
    st = LiveStore(path)
    st.ingest("nas", INST, "s1", [
        hello(1, T0),
        bar(2, T0, 100.0), bar(3, T0 + 3 * MIN, 101.0),
        bar(4, T0, 100.0, "m1"), bar(5, T0 + MIN, 100.5, "m1"), bar(6, T0 + 2 * MIN, 100.7, "m1"),
        entry(7, T0 + 10 * MIN, "orb:2", 1, 100.0, 90.0, 105.0),
        fill(8, T0 + 11 * MIN, "orb:2", "in", 100.25, 2.0),
        fill(9, T0 + 20 * MIN, "orb:2", "out", 105.0, 2.0, "Profit target"),
    ])
    # beh zo Strategy Testera: jeho bary ani obchody nie sú živé dáta
    tester_hello = dict(hello(1, T0 + 100 * MIN, "t1"), tester=True)
    st.ingest("nas", INST, "t1", [tester_hello, bar(2, T0 + 99 * MIN, 500.0)])
    st.close()


def test_export_oddelene_m1_aj_bary_grafu_a_obchody(tmp_path: Path) -> None:
    mirror, root, cursor = tmp_path / "mirror.sqlite", tmp_path / "data_live", tmp_path / "cur.json"
    _mirror(mirror)
    res = livedata.export(mirror, root, cursor, now_ms=T0 + 30 * MIN)
    assert res["candles"] == 5 and res["instances"] == 1 and not res.get("error")
    month = pd.Timestamp(T0, unit="ms", tz="UTC").strftime("%Y-%m")
    sym = root / "candles" / "ninjatrader" / "MNQ"
    assert sorted(p.name for p in sym.iterdir()) == [f"1m-{month}.feather", f"3m-{month}.feather"]
    m1 = livedata.load_candles("ninjatrader", "MNQ", "1m", root)
    assert list(m1.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert m1["open"].tolist() == [100.0, 100.5, 100.7] and str(m1["date"].dt.tz) == "UTC"
    ch = livedata.load_candles("ninjatrader", "MNQ", "3m", root)
    assert ch["open"].tolist() == [100.0, 101.0]            # bar z behu v Testeri (500) tam nie je
    assert (root / "trades" / INST / f"{month}.feather").exists()       # obchody po mesiacoch zatvorenia
    (t,) = livedata.trades(INST, root)
    assert (t["entry"], t["exit"], t["reason"], t["profile"]) == (100.25, 105.0, "take_profit", "PRESIEL_SMERNICAMI_VWAP_ORB_CS_1")
    inst = livedata.instance(INST, root)
    assert [s["session"] for s in inst["sessions"]] == ["s1"] and "PRESIEL_SMERNICAMI_VWAP_ORB_CS_1" in inst["configs"]
    assert inst["instrument"]["point_value"] == 2.0

    # druhý export bez nových udalostí nič neprepíše; súbory ostanú tie isté
    stamps = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    again = livedata.export(mirror, root, cursor, now_ms=T0 + 30 * MIN)
    assert again["candles"] == 0 and again["trades"] == 0 and again["instances"] == 0
    assert stamps == {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}


def test_export_nove_zrkadlo_neprepise_co_uz_je(tmp_path: Path) -> None:
    """Bar, ktorý už v súbore je, vyhráva (reštart zopakuje predhistóriu); obchody z vymeneného zrkadla ostanú."""
    mirror, root, cursor = tmp_path / "mirror.sqlite", tmp_path / "data_live", tmp_path / "cur.json"
    _mirror(mirror)
    livedata.export(mirror, root, cursor, now_ms=T0 + 30 * MIN)
    mirror.unlink()
    st = LiveStore(mirror)
    st.ingest("nas", INST, "s2", [hello(1, T0 + 40 * MIN, "s2"), bar(2, T0, 999.0, "m1"), bar(3, T0 + 3 * MIN, 102.0, "m1")])
    st.close()
    res = livedata.export(mirror, root, cursor, now_ms=T0 + 50 * MIN)
    assert res["candles"] == 1
    assert livedata.load_candles("ninjatrader", "MNQ", "1m", root)["open"].tolist() == [100.0, 100.5, 100.7, 102.0]
    assert len(livedata.trades(INST, root)) == 1
    assert [s["session"] for s in livedata.instance(INST, root)["sessions"]] == ["s1", "s2"]


T0_3M = T0 // (3 * MIN) * 3 * MIN   # bary 3m sú zarovnané na epochu


def _frame(start_ms: int, n: int, minutes: int, px: float) -> pd.DataFrame:
    return pd.DataFrame({"date": pd.to_datetime([start_ms + i * minutes * MIN for i in range(n)], unit="ms", utc=True),
                         "open": px, "high": px + 1, "low": px - 1, "close": px, "volume": 1.0})


def test_combined_minutes_poradie_zdrojov() -> None:
    """Pred hranicou stiahnuté (živé len tam, kde stiahnuté chýbajú); za ňou po baroch grafu živé 1m, inak živý
    bar grafu, inak stiahnuté — zdroje sa v jednom bare nemiešajú."""
    T0 = T0_3M
    b = T0 + 30 * MIN
    official = _frame(T0, 40, 1, 1.0)                       # T0 .. T0+39m
    live_m1 = _frame(T0 + 33 * MIN, 3, 1, 2.0)              # bar 33..35 má 1m zo živého behu
    live_chart = _frame(T0 + 24 * MIN, 6, 3, 3.0)           # bary 24, 27 (pred), 30, 33, 36, 39
    df, counts = livesim.combined_minutes(official, live_m1, live_chart, b, 3)
    assert counts == {"live_1m": 1, "live_chart": 3, "official": 0, "before_live": 0}
    pre = df[df["date"] < pd.Timestamp(b, unit="ms", tz="UTC")]
    assert set(pre["open"]) == {1.0} and len(pre) == 30
    post = df[df["date"] >= pd.Timestamp(b, unit="ms", tz="UTC")]
    assert post["open"].tolist() == [3.0, 2.0, 2.0, 2.0, 3.0, 3.0]

    # stiahnuté končia skôr: pred hranicou doplnia živé bary, za hranicou bez živých dát stiahnuté
    df, counts = livesim.combined_minutes(official[official["date"] < pd.Timestamp(T0 + 27 * MIN, unit="ms", tz="UTC")],
                                          live_m1.iloc[:0], live_chart.iloc[:2], b, 3)
    assert counts["before_live"] == 1 and counts["official"] == 0 and counts["live_chart"] == 0


def test_match_trades_smer_a_cas() -> None:
    real = [{"open": "2026-10-20T14:00:00Z", "dir": "long", "entry": 100.0, "pnl": 50.0, "reason": "sltp", "pts": 5.0},
            {"open": "2026-10-20T18:00:00Z", "dir": "short", "entry": 200.0, "pnl": -10.0, "reason": "stop_loss", "pts": -1.0}]
    sim = [{"open": "2026-10-20T14:03:00Z", "dir": "long", "entry": 100.5, "pnl": 45.0, "reason": "take_profit", "pts": 4.5},
           {"open": "2026-10-20T18:00:00Z", "dir": "long", "entry": 200.0, "pnl": 10.0, "reason": "take_profit", "pts": 1.0}]
    m = livesim.match_trades(real, sim, 3)
    (p,) = m["pairs"]
    assert (p["real"], p["sim"], p["dt_min"], p["d_entry"], p["d_pnl"], p["same_exit"]) == (0, 0, -3.0, -0.5, 5.0, True)
    assert m["only_real"] == [1] and m["only_sim"] == [1]   # iný smer nie je ten istý obchod


def test_api_livedata_behy_a_pohlad(tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from tester.webapp import app as app_mod
    from tester.webapp.store import RunStore

    mirror, root = tmp_path / "mirror.sqlite", tmp_path / "data_live"
    _mirror(mirror)
    livedata.export(mirror, root, tmp_path / "cur.json", now_ms=T0 + 30 * MIN)
    monkeypatch.setattr(livedata, "LIVE_DATA", root)
    monkeypatch.setattr(livedata, "LIVE_DATA_HUB", tmp_path / "nic")
    c = TestClient(app_mod.create_app(RunStore(tmp_path / "runs")))
    (run,) = c.get("/api/diversify/livedata").json()["runs"]
    assert (run["instance"], run["profile"], run["trades"], run["engine"]) == (INST, "PRESIEL_SMERNICAMI_VWAP_ORB_CS_1", 1, "vwaporbnet")
    v = c.get("/api/diversify/livedata/view", params={"instance": INST, "profile": run["profile"]}).json()
    assert v["boundary"] == "2026-10-14T17:46:40Z" and len(v["real"]) == 1 and "configs" not in v["instance"]
    assert v["chart"]["after"] and v["sources"]["live_1m"] == 2   # T0 nie je na hranici 3m baru
    assert c.get("/api/diversify/livedata/view", params={"instance": "nie"}).status_code == 404


# --------------------------------------------------------------------------- #
# git + hub: čítanie z dvoch koreňov, sync z hubu, plugin hubu (export, ponuka, mesačný push)
# --------------------------------------------------------------------------- #


def test_citanie_spaja_git_a_hub(tmp_path: Path, monkeypatch) -> None:
    """Bez `root` číta git (`LIVE_DATA`) aj to, čo je len na hube (`LIVE_DATA_HUB`); ten istý bar z hubu vyhrá."""
    git_root, hub_root = tmp_path / "git", tmp_path / "hub"
    m = pd.Timestamp(T0, unit="ms", tz="UTC").strftime("%Y-%m")
    for root, px in ((git_root, 1.0), (hub_root, 2.0)):
        d = livedata.symbol_dir("mt5", "US100.cash", root)
        d.mkdir(parents=True)
        start = T0 if root is git_root else T0 + 2 * MIN
        _frame(start, 3, 1, px).to_feather(d / f"1m-{m}.feather")
    monkeypatch.setattr(livedata, "LIVE_DATA", git_root)
    monkeypatch.setattr(livedata, "LIVE_DATA_HUB", hub_root)
    df = livedata.load_candles("mt5", "US100.cash")
    assert df["open"].tolist() == [1.0, 1.0, 2.0, 2.0, 2.0]          # T0+2m je v oboch — platí hub


class FakeHubHttp:
    """`HubHttp` nad stromom pluginu: zoznam a súbory ako `GET /api/plugins/livedata/files[/<cesta>]`."""

    def __init__(self, root: Path, offered: set[str] | None = None) -> None:
        self.root, self.offered, self.downloads = root, offered, 0

    def _files(self):
        return [f for f in livedata.file_index(self.root) if self.offered is None or f["path"] in self.offered]

    def get(self, path: str):
        assert path == livedata.HUB_FILES
        return {"files": self._files()}

    def get_bytes(self, path: str) -> bytes:
        from urllib.parse import unquote

        rel = unquote(path[len(livedata.HUB_FILES) + 1:])
        assert rel in {f["path"] for f in self._files()}
        self.downloads += 1
        return (self.root / rel).read_bytes()


def test_sync_hub_stiahne_len_co_nie_je_v_gite_a_upratuje_az_ked_to_git_ma(tmp_path: Path) -> None:
    mirror, hub_root, cache, repo = tmp_path / "mirror.sqlite", tmp_path / "hub", tmp_path / "cache", tmp_path / "repo"
    _mirror(mirror)
    livedata.export(mirror, hub_root, tmp_path / "cur.json", now_ms=T0 + 30 * MIN)
    http = FakeHubHttp(hub_root)
    res = livedata.sync_hub(http, cache, repo)
    n = len(livedata.file_index(hub_root))
    assert res == {"files": n, "downloaded": n, "removed": 0}
    assert livedata.file_index(cache) == livedata.file_index(hub_root)
    assert livedata.sync_hub(http, cache, repo)["downloaded"] == 0 and http.downloads == n   # nič nové

    # hub pushol sviečky (už ich neponúka); kým ich webapp nemá z gitu, z cache nezmiznú
    http.offered = {f["path"] for f in livedata.file_index(hub_root) if not f["path"].startswith("candles/")}
    assert livedata.sync_hub(http, cache, repo)["removed"] == 0
    for f in livedata.file_index(hub_root):
        if f["path"].startswith("candles/"):
            (repo / f["path"]).parent.mkdir(parents=True, exist_ok=True)
            (repo / f["path"]).write_bytes((hub_root / f["path"]).read_bytes())
    assert livedata.sync_hub(http, cache, repo)["removed"] == 2
    assert not any(f["path"].startswith("candles/") for f in livedata.file_index(cache))


def _git(*args: str, cwd: Path) -> str:
    import subprocess

    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True,
                          encoding="utf-8").stdout.strip()


def _bare_repo(tmp_path: Path) -> Path:
    bare, seed = tmp_path / "origin.git", tmp_path / "seed"
    _git("init", "-q", "--bare", "-b", "main", str(bare), cwd=tmp_path)
    seed.mkdir()
    _git("init", "-q", "-b", "main", cwd=seed)
    (seed / "README.md").write_text("repo\n", encoding="utf-8")
    _git("add", ".", cwd=seed)
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init", cwd=seed)
    _git("push", "-q", str(bare), "main", cwd=seed)
    return bare


def test_plugin_hubu_exportuje_ponuka_mimo_gitu_a_pushne_uzavrety_mesiac(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    import json as _json
    import shutil

    if shutil.which("git") is None:
        pytest.skip("git nie je")
    from tester.hub.plugins import PluginHost
    from tester.hub.plugins.livedata.plugin import LiveData

    mirror = tmp_path / "live.sqlite"
    _mirror(mirror)
    bare = _bare_repo(tmp_path)
    cfg_dir = tmp_path / "plugins" / "livedata"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.json").write_text(_json.dumps({"source": str(mirror), "remote": str(bare), "push_day": 2}),
                                         encoding="utf-8")
    month = pd.Timestamp(T0, unit="ms", tz="UTC")
    in_month = month.timestamp() + 3600                                   # ešte ten istý mesiac
    nxt = (month + pd.offsets.MonthBegin(1)).normalize()
    t = [in_month]
    host = PluginHost(tmp_path / "plugins", None, None, classes={"livedata": LiveData}, clock=lambda: t[0])
    p = host.get("livedata")

    assert host.run_once("livedata")
    offered = {f["path"] for f in host.files("livedata")}
    assert any(x.startswith("candles/") for x in offered) and any(x.startswith("trades/") for x in offered)
    assert p.status()["pending_months"] == [month.strftime("%Y-%m")] and not p.due(t[0])
    rel = sorted(offered)[0]
    assert host.file_path("livedata", rel).read_bytes() == (p.root / rel).read_bytes()
    with pytest.raises(KeyError):
        host.file_path("livedata", "../config.json")                      # len to, čo je v zozname

    t[0] = nxt.timestamp() + 3600                                         # 1. deň ďalšieho mesiaca: ešte nie
    assert host.run_once("livedata") and _git("rev-list", "--count", "main", cwd=bare) == "1"
    t[0] = (nxt + pd.Timedelta(days=1)).timestamp() + 3600                # 2. deň: push
    assert host.run_once("livedata")
    assert _git("rev-list", "--count", "main", cwd=bare) == "2"
    tree = set(_git("ls-tree", "-r", "--name-only", "main", cwd=bare).splitlines())
    assert {f"data_live/{x}" for x in offered} <= tree and "README.md" in tree
    assert "Pridaj živé dáta za " + month.strftime("%Y-%m") in _git("log", "-1", "--format=%s", "main", cwd=bare)
    assert host.files("livedata") == [] and p.status()["last_commit"]
    # ďalšie kolo bez zmien nič necommitne
    p.push_tried = 0.0
    assert host.run_once("livedata") and _git("rev-list", "--count", "main", cwd=bare) == "2"


def test_hub_subory_pluginu_cez_api(tmp_path: Path) -> None:
    """`GET /api/plugins/<meno>/files[/<cesta>]`: zoznam a súbor, ktorý plugin ponúka; nič iné (ani `..`)."""
    pytest.importorskip("fastapi")
    import time

    from fastapi.testclient import TestClient

    from tester.hub.plugins import HubPlugin, PluginHost
    from tester.hub.server import HubState, create_hub_app

    data = tmp_path / "data"
    (data / "candles" / "x").mkdir(parents=True)
    (data / "candles" / "x" / "1m-2026-10.feather").write_bytes(b"abc")
    (data / "tajne.txt").write_bytes(b"nie")

    class Files(HubPlugin):
        def files(self):
            return [{"path": "candles/x/1m-2026-10.feather", "sha": "s"}]

        def files_root(self):
            return data

    st = HubState(root=tmp_path / "hub", token=None)
    app = create_hub_app(st)
    st.plugins = PluginHost(tmp_path / "hub" / "plugins", st, None, classes={"livedata": Files, "nic": HubPlugin},
                            clock=time.time)
    cl = TestClient(app)
    assert cl.get("/api/plugins/livedata/files").json() == {"files": [{"path": "candles/x/1m-2026-10.feather", "sha": "s"}]}
    assert cl.get("/api/plugins/livedata/files/candles/x/1m-2026-10.feather").content == b"abc"
    assert cl.get("/api/plugins/livedata/files/tajne.txt").status_code == 404
    assert cl.get("/api/plugins/livedata/files/candles/../tajne.txt").status_code == 404
    assert cl.get("/api/plugins/nic/files").status_code == 404
